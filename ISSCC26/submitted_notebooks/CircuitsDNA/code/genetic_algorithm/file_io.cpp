#include "file_io.h"

#include <fstream>
#include <sstream>
#include <optional>
#include <unordered_map>
#include <vector>
#include <string>
#include <iostream>

using namespace std;

// ===================== Netlist Loader (unsigned 8-bit) =====================
// Supports lines like:

bool load_verilog(const string& path, Circuit& out) {
    ifstream fin(path);
    if (!fin.is_open()) { cerr << "[Loader] cannot open " << path << endl; return false; }

    vector<Node> nodes;
    unordered_map<string,Ref> sym; // net name -> Ref (node output)
    auto to_lower = [](string s){ for (auto& c:s) c = (char)tolower(c); return s; };

    // Map cell token like "gf180...__and2_1" -> GateName
    auto gate_from_token = [&](const string& t)->optional<GateName> {
        string s = to_lower(t);
        // fast path for simple tokens too
        if (s=="and2" || s.find("__and2_")!=string::npos)   return GateName::AND;
        if (s=="nand2"|| s.find("__nand2_")!=string::npos)  return GateName::NAND;
        if (s=="or2"  || s.find("__or2_")!=string::npos)    return GateName::OR;
        if (s=="xor2" || s.find("__xor2_")!=string::npos)   return GateName::XOR;
        if (s=="xnor2"|| s.find("__xnor2_")!=string::npos)  return GateName::XNOR;
        if (s=="inv"  || s.find("__inv_")!=string::npos)    return GateName::INV;
        return nullopt;
    };

    auto is_attr_or_comment = [](const string& l)->bool {
        string s = trim(l);
        if (s.empty()) return true;
        if (s.rfind("//",0)==0) return true;
        if (s.rfind("/*",0)==0) return true;
        if (s.rfind("(*",0)==0) return true;
        return false;
    };

    // small helpers for inputs A[k]/B[k]
    auto ref_from_AB = [&](const string& tok)->optional<Ref> {
        // formats "A[3]" or "B[7]"
        if (tok.size()<4) return nullopt;
        if (tok[1]!='[') return nullopt;
        if ((tok[0]!='A' && tok[0]!='B')) return nullopt;
        auto rb = tok.rfind(']');
        if (rb==string::npos) return nullopt;
        int idx = stoi(tok.substr(2, rb-2));
        if (idx<0 || idx>7) throw runtime_error("A/B index out of range: " + tok);
        int flat = (tok[0]=='A') ? idx : (8+idx);
        return Ref{true, flat, 0};
    };

    string buf;
    int line_no = 0;
    auto flush_gate_line = [&](const string& full)->bool {
        // full like:  cell inst ( .A1(B[0]), .A2(A[0]), .Z(OUT[0]) );
        string one = trim(strip_tail_semicolon(full));
        if (one.empty()) return true;

        // 1) first two tokens: gate token + inst name
        string gatetok, unitname;
        {
            stringstream ss(one);
            ss >> gatetok >> unitname;
        }
        auto gopt = gate_from_token(gatetok);
        if (!gopt) return true; // ignore non-supported cells
        GateName g = *gopt;

        // 2) extract pin section between first '(' and last ')'
        size_t lp = one.find('(');
        size_t rp = one.rfind(')');
        if (lp==string::npos || rp==string::npos || rp<=lp) {
            cerr << "[Loader] bad instance pins near line " << line_no << "\n  text: " << full << endl;
            return false;
        }
        string pins = one.substr(lp+1, rp-(lp+1));

        // 3) split by commas at depth 0
        vector<string> parts;
        {
            string cur; int depth=0;
            for (char c: pins) {
                if (c=='(') ++depth;
                else if (c==')') --depth;
                if (c==',' && depth==0) { parts.push_back(trim(cur)); cur.clear(); }
                else cur.push_back(c);
            }
            if (!cur.empty()) parts.push_back(trim(cur));
        }

        string A1, A2, AI, Y; // accept .A1, .A2, .A, .B, .I and .Z/.ZN
        for (auto t: parts) {
            size_t l = t.find('('), r = t.rfind(')');
            if (l==string::npos || r==string::npos || r<=l+1) continue;
            string pin = trim(t.substr(0,l));
            string val = trim(t.substr(l+1, r-(l+1)));
            string pl = to_lower(pin);
            if (pl==".a1" || pl==".a") A1 = val;
            else if (pl==".a2" || pl==".b") A2 = val;
            else if (pl==".i") AI = val;
            else if (pl==".z" || pl==".zn") Y = val;
        }

        // Normalize inputs vector according to gate arity
        vector<Ref> ins;
        try {
            auto push_tok = [&](const string& tok){
                if (tok.empty()) throw runtime_error("missing pin token");
                // first: A[k]/B[k]
                if (auto ra = ref_from_AB(tok)) { ins.push_back(*ra); return; }
                // else: previously defined net or OUT[...] (as wire on RHS; rare but fine)
                auto it = sym.find(tok);
                if (it!=sym.end()) { ins.push_back(it->second); return; }
                throw runtime_error("unknown net on RHS: " + tok);
            };

            if (g==GateName::INV) {
                if (AI.empty()) throw runtime_error(".I missing for INV");
                push_tok(AI);
            } else {
                // some libs may put only A1/A2; order doesn't matter
                if (A1.empty() || A2.empty()) throw runtime_error(".A1/.A2 missing");
                push_tok(A1); push_tok(A2);
            }
        } catch (const exception& e) {
            cerr << "[Loader] line " << line_no << " : " << e.what() << "\n  text: " << full << endl;
            return false;
        }

        int new_idx = (int)nodes.size();
        nodes.push_back(Node{g, move(ins)});

        // record destination net
        if (!Y.empty()) {
            // normal net name
            sym[Y] = Ref{false, new_idx, 0};

            // if it's OUT[k], also record OUT#k for later collection
            if (Y.rfind("OUT[",0)==0) {
                int bit = index_in_brackets(Y); // your helper: returns inside [...]
                if (bit>=0 && bit<NUM_OUT) {
                    sym["OUT#"+to_string(bit)] = Ref{false, new_idx, 0};
                }
            }
        }
        return true;
    };

    string line;
    bool in_instance = false;
    string inst_accum;

    while (getline(fin, line)) {
        ++line_no;
        string raw = line;
        string s = trim(line);
        if (s.empty() || is_attr_or_comment(s)) continue;
        if (s.rfind("module ",0)==0 || s.find("endmodule")!=string::npos
         || s.rfind("input ",0)==0  || s.rfind("output ",0)==0
         || s.rfind("wire ",0)==0) continue;

        // start or continue an instance
        if (!in_instance) {
            // check if this looks like a cell line
            // grab first token to see if we recognize the cell
            string tok;
            {
                stringstream ss(s);
                ss >> tok;
            }
            if (gate_from_token(tok)) {
                in_instance = true;
                inst_accum.clear();
                inst_accum += s;
                // if the same line already ends with ");", flush immediately
                if (s.find(");") != string::npos) {
                    if (!flush_gate_line(inst_accum)) return false;
                    in_instance = false;
                    inst_accum.clear();
                }
                continue;
            } else {
                // ignore everything else
                continue;
            }
        } else {
            // accumulating pins until ");
            inst_accum += " " + s;
            if (s.find(");") != string::npos) {
                if (!flush_gate_line(inst_accum)) return false;
                in_instance = false;
                inst_accum.clear();
            }
            continue;
        }
    }
    if (in_instance) {
        cerr << "[Loader] unexpected EOF while parsing instance near line " << line_no << endl;
        return false;
    }

    // Build Circuit
    Circuit c;
    c.nodes = move(nodes);
    c.outputs.assign(NUM_OUT, Ref{true, 0, 0});
    for (int o = 0; o < NUM_OUT; ++o) {
        string k1 = "OUT#" + to_string(o);
        string k2 = "OUT0#" + to_string(o); // legacy compatibility
        auto it = sym.find(k1);
        if (it == sym.end()) it = sym.find(k2);
        if (it != sym.end()) c.outputs[o] = it->second;
        else {
            int pos = (int)c.nodes.size();
            c.nodes.push_back(Node{GateName::CONST0, {}});
            c.outputs[o] = Ref{false, pos, 0};
        }
    }

    out = prune_inactive(c);
    return true;
}



// ===================== Dump netlist =====================
void dump_netlist(const Circuit& c, const string& fn) {
    ofstream ofs(fn);
    if (!ofs.is_open()) { cerr << "cannot write " << fn << endl; return; }
    ofs << "# Netlist\n";
    for (int i = 0; i < NUM_IN; ++i) ofs << "INPUT n" << i << '\n';
    ofs << '\n';

    for (size_t j = 0; j < c.nodes.size(); ++j) {
        const auto& n = c.nodes[j];
        int oarity = arity_out(n.gate);
        vector<string> outs; outs.reserve(oarity);
        for (int k = 0; k < oarity; ++k) outs.push_back("v"+to_string(j)+"_"+to_string(k));

        vector<string> ins; ins.reserve(n.inputs.size());
        for (const auto& r : n.inputs) {
            if (r.is_input) ins.push_back("n"+to_string(r.idx));
            else            ins.push_back("v"+to_string(r.idx)+"_"+to_string(r.slot));
        }

        ofs << (outs.empty() ? string("-") : outs[0]);
        for (size_t k = 1; k < outs.size(); ++k) ofs << ", " << outs[k];
        ofs << " = " << gname(n.gate) << "(";
        for (size_t k = 0; k < ins.size(); ++k) { if (k) ofs << ", "; ofs << ins[k]; }
        ofs << ")\n\n";
    }
    for (int o = 0; o < NUM_OUT; ++o) {
        const auto& r = c.outputs[o];
        string src = r.is_input ? ("n"+to_string(r.idx))
                                : ("v"+to_string(r.idx)+"_"+to_string(r.slot));
        ofs << "OUT" << o << " = " << src << '\n';
    }
    ofs.close();
    cerr << "[Dump] wrote " << fn << endl;
}

// ===================== Log file dump =====================
void log_progress_txt(int gen, double best_fit,
                      const Circuit& best, const ErrorStats& es,
                      const string& logfile)
{
    static ofstream lf;
    static string   opened_name;
    if (!lf.is_open() || opened_name != logfile) {
        if (lf.is_open()) lf.close();
        lf.open(logfile, ios::out | ios::trunc);
        if (!lf.is_open()) {
            cerr << "[Log] cannot open " << logfile << " for writing.\n";
            return;
        }
    lf << "# gen eps_th best_fit nodes NMED ER WCE MRE sMAPE\n";
        opened_name = logfile;
    }

     lf << gen << " "
         << eps_th << " "
         << best_fit << " "
         << best.nodes.size() << " "
         << es.NMED << " "
         << es.ER   << " "
         << es.WCE  << " "
         << es.MRE  << " "
         << es.sMAPE << "\n";
    lf.flush();
}
