#include "main.h"
#include "problem.h"
#include "gate.h"
#include "utils.h"
#include "file_io.h"
#include <filesystem>

using namespace std;

// Configurations (runtime-overridable defaults)
bool            LOAD_FROM_FILE = true;
bool            SIGNED_MULT    = true;
std::string     NETLIST_FILE   = "mult_8bits.syn.v";
std::string     OUTPUT_DIR     = "results/genetic_algorithm";
std::string     logfile        = std::string(OUTPUT_DIR) + "/evolution_metrics_signed8x8.txt";
int             GENERATIONS    = 1000000;
int             POP_SIZE       = 100;
double          TOP_K_RATIO    = 0.02;
double          EPS_START      = 0.0;
double          EPS_END        = 0.01;
double          EPS_TAU        = 2000.0;
uint32_t        SEED           = 2025;

std::array<double,6> MUT_WEIGHTS { 0.10, 0.10, 0.10, 0.40, 0.15, 0.15};

const double   HUGE_PENALTY   = 1e6;
int            MAX_TRUE_ABS   = 0;
std::mt19937   rng;

double         eps_th         = 0.0;
// ===================== Evaluate whole circuit =====================
array<array<uint8_t,NUM_OUT>,B> evaluate(const Circuit& c){
    array<vector<uint8_t>,NUM_IN> inbits;
    for(int i=0;i<NUM_IN;++i){
        inbits[i].resize(B);
        for(int b=0;b<B;++b) inbits[i][b]=ALL_INPUTS[b][i]&1;
    }
    vector<vector<vector<uint8_t>>> node_outs; // [node][slot][b]
    node_outs.reserve(c.nodes.size());
    for(size_t j=0;j<c.nodes.size();++j){
        const Node& n=c.nodes[j];
        vector<vector<uint8_t>> ins;
        ins.reserve(n.inputs.size());
        for(const auto& r: n.inputs){
            if(r.is_input) ins.push_back(inbits[r.idx]);
            else           ins.push_back(node_outs[r.idx][r.slot]);
        }
        node_outs.push_back(eval_gate(n.gate, ins));
    }
    array<array<uint8_t,NUM_OUT>,B> Y{};
    for(int o=0;o<NUM_OUT;++o){
        const Ref& r=c.outputs[o];
        for(int b=0;b<B;++b){
            Y[b][o] = r.is_input ? (inbits[r.idx][b]&1)
                                 : (node_outs[r.idx][r.slot][b]&1);
        }
    }
    return Y;
}

double fitness(const Circuit& c, ErrorStats* out){
    auto Y = evaluate(c);
    long long sum_abs=0;      // L1
    long long err_cnt=0;      // count of mismatches
    long long worst=0;        // max |error|

    long double sum_rel_ex0=0.0L; // mean relative error (exclude zero GT)
    long long   cnt_rel=0;
    long double sum_smape=0.0L;   // sMAPE

    for(int b=0;b<B;++b){
        uint16_t gt_u=0, ap_u=0;
        for(int i=0;i<NUM_OUT;++i){
            if(ALL_TARGETS[b][i]&1) gt_u = setb(gt_u,i,1);
            if(Y[b][i]&1)           ap_u = setb(ap_u,i,1);
        }

        int16_t gt = static_cast<int16_t>(gt_u);
        int16_t ap = static_cast<int16_t>(ap_u);

        long long diff = (long long)gt - (long long)ap;
        long long ad   = llabs(diff);
        sum_abs += ad;
        if(ad) ++err_cnt;
        worst = std::max(worst, ad);

        long long ay_abs  = llabs((long long)gt);
        long long ayp_abs = llabs((long long)ap);

        if(ay_abs > 0) {                       // MRE
            sum_rel_ex0 += (long double)ad / (long double)ay_abs;
            ++cnt_rel;
        }

        long double denom = 0.5L*((long double)ay_abs + (long double)ayp_abs) + 1e-9L;
        sum_smape += (long double)ad / denom;
    }

    double NMED = (double)sum_abs / ((double)B * (double)MAX_TRUE_ABS);
    double ER   = (double)err_cnt / (double)B;
    double WCE  = (double)worst   / (double)MAX_TRUE_ABS;
    double MRE  = (cnt_rel>0) ? (double)(sum_rel_ex0 / (long double)cnt_rel) : 0.0;
    double sMAPE= (double)(sum_smape / (long double)B);

    if(out){ out->NMED=NMED; out->ER=ER; out->WCE=WCE; out->MRE=MRE; out->sMAPE=sMAPE; }

    double area = (double)circuit_area_mos(c);
    return (WCE <= eps_th) ? area : area + HUGE_PENALTY*(WCE - eps_th);
}


// ===================== Mutations =====================
Ref random_input_ref(){ return Ref{true, rint(0,NUM_IN-1),0}; }
Ref random_ref_any(int nodes, const vector<int>& oarity){
    vector<Ref> cs; cs.reserve(NUM_IN + nodes*2);
    for(int i=0;i<NUM_IN;++i) cs.push_back(Ref{true,i,0});
    for(int j=0;j<nodes;++j) for(int k=0;k<oarity[j];++k) cs.push_back(Ref{false,j,k});
    return cs[rint(0,(int)cs.size()-1)];
}
Ref random_ref_before_node(int node_idx, const vector<int>& oarity){
    vector<Ref> cs; cs.reserve(NUM_IN + node_idx*2);
    for(int i=0;i<NUM_IN;++i) cs.push_back(Ref{true,i,0});
    for(int j=0;j<node_idx;++j) for(int k=0;k<oarity[j];++k) cs.push_back(Ref{false,j,k});
    return cs[rint(0,(int)cs.size()-1)];
}

void fix_refs_on_insert(Circuit& c, int pos){
    for(auto& n:c.nodes){
        for(auto& r:n.inputs) if(!r.is_input && r.idx>=pos) r.idx+=1;
    }
    for(auto& r:c.outputs) if(!r.is_input && r.idx>=pos) r.idx+=1;
}

Circuit prune_inactive(const Circuit& c){
    if(c.nodes.empty()) return c;
    int n=c.nodes.size();
    vector<char> active(n,0);
    vector<int> st;
    for(const auto& r:c.outputs) if(!r.is_input){
        if(!active[r.idx]){ active[r.idx]=1; st.push_back(r.idx); }
    }
    while(!st.empty()){
        int u=st.back(); st.pop_back();
        for(const auto& r:c.nodes[u].inputs){
            if(!r.is_input && !active[r.idx]){ active[r.idx]=1; st.push_back(r.idx); }
        }
    }
    int cnt = accumulate(active.begin(),active.end(),0);
    if(cnt==n) return c;

    vector<int> keep; keep.reserve(cnt);
    for(int i=0;i<n;++i) if(active[i]) keep.push_back(i);
    unordered_map<int,int> remap;
    for(int i=0;i<(int)keep.size();++i) remap[keep[i]]=i;

    Circuit out;
    out.nodes.reserve(keep.size());
    for(int old:keep){
        const Node& nn=c.nodes[old];
        Node m; m.gate=nn.gate;
        for(const auto& r: nn.inputs){
            if(r.is_input) m.inputs.push_back(r);
            else m.inputs.push_back(Ref{false, remap.at(r.idx), r.slot});
        }
        out.nodes.push_back(move(m));
    }
    vector<int> oa = out.out_arity();
    for(const auto& r:c.outputs){
        if(r.is_input) out.outputs.push_back(r);
        else{
            auto it=remap.find(r.idx);
            if(it==remap.end()) out.outputs.push_back(random_ref_any(out.nodes.size(),oa));
            else{
                int ni=it->second;
                int sl = (r.slot<oa[ni])?r.slot:0;
                out.outputs.push_back(Ref{false,ni,sl});
            }
        }
    }
    return out;
}

GateName random_gate(){
    const vector<GateName> G = {
        GateName::AND, GateName::NAND, GateName::OR, GateName::XOR, GateName::XNOR, GateName::INV
    };
    return G[rint(0,(int)G.size()-1)];
}

Circuit mutate_add_node(const Circuit& c){
    Circuit nc=c;
    int pos=rint(0,(int)nc.nodes.size());
    fix_refs_on_insert(nc,pos);

    GateName g=random_gate();
    int in_a = arity_in(g);
    vector<int> oa = nc.out_arity();
    vector<Ref> ins;
    if(in_a>0){
        if(pos==0){ for(int t=0;t<in_a;++t) ins.push_back(random_input_ref()); }
        else{ for(int t=0;t<in_a;++t) ins.push_back(random_ref_before_node(pos,oa)); }
    }
    nc.nodes.insert(nc.nodes.begin()+pos, Node{g,move(ins)});
    int new_o = arity_out(g);
    // randomly connect its outputs into downstream consumers or to OUTs
    vector<pair<int,int>> consumers;
    for(int j=pos+1;j<(int)nc.nodes.size();++j){
        int in = arity_in(nc.nodes[j].gate);
        for(int w=0; w<in; ++w) consumers.emplace_back(j,w);
    }
    if(!consumers.empty() && new_o>0){
        shuffle(consumers.begin(),consumers.end(),rng);
        int m = max(1,min(new_o,(int)consumers.size()));
        for(int t=0;t<m;++t){
            auto [j,w]=consumers[t];
            nc.nodes[j].inputs[w]=Ref{false,pos,rint(0,new_o-1)};
        }
    }else{
        if(new_o>0){
            int o=rint(0,NUM_OUT-1);
            nc.outputs[o]=Ref{false,pos,rint(0,new_o-1)};
        }
    }
    return nc;
}

Circuit mutate_del_node_idx(const Circuit& c, int victim){
    if(c.nodes.empty()) return c;
    if(victim<0 || victim>=(int)c.nodes.size()) return c;
    Circuit nc=c;
    nc.nodes.erase(nc.nodes.begin()+victim);
    vector<int> oa = nc.out_arity();
    auto fix=[&](Ref r,int cons,bool is_out)->Ref {
        if(r.is_input) return r;
        if(r.idx==victim){
            if(is_out) return random_ref_any(nc.nodes.size(),oa);
            if(cons<=0) return random_input_ref();
            return random_ref_before_node(cons, oa);
        }
        if(r.idx>victim){
            int ni=r.idx-1;
            int sl = (ni<(int)oa.size() && r.slot<oa[ni])?r.slot:0;
            return Ref{false,ni,sl};
        }
        return r;
    };
    for(int j=0;j<(int)nc.nodes.size();++j){
        for(auto& r:nc.nodes[j].inputs) r=fix(r,j,false);
    }
    for(auto& r:nc.outputs) r=fix(r,-1,true);
    return nc;
}
Circuit mutate_del_node(const Circuit& c){
    if(c.nodes.empty()) return c;
    return mutate_del_node_idx(c, rint(0,(int)c.nodes.size()-1));
}

Circuit mutate_rewire_in_idx(const Circuit& c, int j){
    if(c.nodes.empty()) return c;
    if(j<0||j>=(int)c.nodes.size()) return c;
    Circuit nc=c;
    int in_a=arity_in(nc.nodes[j].gate);
    if(in_a==0) return c;
    int which=rint(0,in_a-1);
    vector<int> oa=nc.out_arity();
    if(j>0) nc.nodes[j].inputs[which]=random_ref_before_node(j,oa);
    else    nc.nodes[j].inputs[which]=random_input_ref();
    return nc;
}
Circuit mutate_rewire_in(const Circuit& c){
    return mutate_rewire_in_idx(c, rint(0,(int)c.nodes.size()-1));
}

Circuit mutate_change_gate_idx(const Circuit& c, int j){
    if(c.nodes.empty()) return c;
    if(j<0||j>=(int)c.nodes.size()) return c;
    Circuit nc=c;
    GateName old = nc.nodes[j].gate;
    GateName ng  = random_gate();
    if(ng==old) ng = random_gate();
    int old_in=arity_in(old), new_in=arity_in(ng);
    vector<Ref> cur=nc.nodes[j].inputs, neo;
    if(new_in>old_in){
        neo=cur;
        vector<int> oa=nc.out_arity();
        for(int t=0;t<new_in-old_in;++t){
            if(j==0) neo.push_back(random_input_ref());
            else     neo.push_back(random_ref_before_node(j,oa));
        }
    }else if(new_in<old_in){
        neo.clear();
        vector<int> idx(old_in); iota(idx.begin(),idx.end(),0);
        shuffle(idx.begin(),idx.end(),rng);
        idx.resize(new_in);
        sort(idx.begin(),idx.end());
        for(int id:idx) neo.push_back(cur[id]);
    }else neo=cur;
    nc.nodes[j].gate=ng;
    nc.nodes[j].inputs=move(neo);
    return nc;
}
Circuit mutate_change_gate(const Circuit& c){
    return mutate_change_gate_idx(c, rint(0,(int)c.nodes.size()-1));
}

Circuit mutate_rewire_out(const Circuit& c){
    Circuit nc=c;
    vector<int> oa=nc.out_arity();
    int o=rint(0,NUM_OUT-1);
    nc.outputs[o]=random_ref_any(nc.nodes.size(), oa);
    return nc;
}

inline bool is_commutative(GateName g){
    switch(g){
        case GateName::AND: case GateName::NAND:
        case GateName::OR:  case GateName::XOR:
        case GateName::XNOR: return true;
        default: return false;
    }
}

Circuit mutate_merge_equiv(const Circuit& c){
    if(c.nodes.size()<2) return c;
    Circuit nc = c;
    auto key_of = [&](int i){
        std::vector<std::tuple<bool,int,int>> vv;
        vv.reserve(nc.nodes[i].inputs.size());
        for(const auto& r: nc.nodes[i].inputs) vv.emplace_back(r.is_input, r.idx, r.slot);
        if(is_commutative(nc.nodes[i].gate)) std::sort(vv.begin(), vv.end());
        return std::make_pair(nc.nodes[i].gate, vv);
    };
    int N = (int)nc.nodes.size();
    for(int j=1;j<N;++j){
        auto kj = key_of(j);
        for(int i=0;i<j;++i){
            if(nc.nodes[i].gate!=nc.nodes[j].gate) continue;
            auto ki = key_of(i);
            if(ki != kj) continue;
            for(auto& nd: nc.nodes){
                for(auto& r: nd.inputs){
                    if(!r.is_input && r.idx==j) r.idx = i;
                }
            }
            for(auto& r: nc.outputs){
                if(!r.is_input && r.idx==j) r.idx = i;
            }
            // 删除 j
            nc = mutate_del_node_idx(nc, j);
            return prune_inactive(nc);
        }
    }
    return c;
}

Circuit mutate_merge_all_equiv(Circuit c, int max_iter = 64){
    if(c.nodes.size() < 2) return c;
    for(int it = 0; it < max_iter; ++it){
        Circuit nc = mutate_merge_equiv(c);
        if(nc.nodes.size() == c.nodes.size()) {
            break;
        }
        c = std::move(nc);
    }
    return c;
}

// Weighted random choice over mutation ops
Circuit random_mutation(const Circuit& c){
    double r = uniform_real_distribution<double>(0.0,1.0)(rng);
    double acc=0;
    for(size_t i=0;i<MUT_WEIGHTS.size();++i){
        acc += MUT_WEIGHTS[i];
        if(r<acc){
            switch(i){
                case 0: return mutate_add_node(c);
                case 1: return mutate_del_node(c);
                case 2: return mutate_change_gate(c);
                case 3: return mutate_merge_all_equiv(c);
                case 4: return mutate_rewire_in(c);
                case 5: return mutate_rewire_out(c);
            }
        }
    }
    return c;
}

// ===================== Random init (fallback) =====================
Circuit random_initial_circuit(int min_nodes,int max_nodes){
    Circuit c;
    int k=rint(min_nodes,max_nodes);
    c.nodes.reserve(k);
    for(int j=0;j<k;++j){
        GateName g=random_gate();
        int in_a=arity_in(g);
        vector<int> oa=c.out_arity();
        vector<Ref> ins;
        if(in_a>0){
            if(j==0){ for(int t=0;t<in_a;++t) ins.push_back(random_input_ref()); }
            else{ for(int t=0;t<in_a;++t) ins.push_back(random_ref_before_node(j,oa)); }
        }
        c.nodes.push_back(Node{g,move(ins)});
    }
    vector<int> oa=c.out_arity();
    c.outputs.resize(NUM_OUT);
    for(int o=0;o<NUM_OUT;++o) c.outputs[o]=random_ref_any(c.nodes.size(),oa);
    return prune_inactive(c);
}

// ===================== Evolution driver =====================
pair<double,Circuit> evolve(const Circuit& seed){
    vector<Circuit> pop; pop.reserve(POP_SIZE);
    pop.push_back(seed);
    while((int)pop.size()<POP_SIZE){
        Circuit c=pop.back();
        c = random_mutation(c);
        c = prune_inactive(c);
        pop.push_back(move(c));
    }
    vector<double> fits(POP_SIZE,0.0);

    double best_fit = 1e300;
    Circuit best;

    for(int gen=1; gen<=GENERATIONS; ++gen){
        eps_th = EPS_END + (EPS_START - EPS_END) * exp(-(double)gen / EPS_TAU);
        for(int i=0;i<POP_SIZE;++i) fits[i]=fitness(pop[i],nullptr);
        int best_i = (int)(min_element(fits.begin(),fits.end())-fits.begin());
        if(fits[best_i]<best_fit){ best_fit=fits[best_i]; best=pop[best_i]; }

        // selection
        int mu = max(1, (int)ceil(TOP_K_RATIO*POP_SIZE));
        vector<int> idx(POP_SIZE); iota(idx.begin(),idx.end(),0);
        nth_element(idx.begin(), idx.begin()+mu, idx.end(), [&](int a,int b){ return fits[a]<fits[b]; });
        idx.resize(mu);
        sort(idx.begin(),idx.end(),[&](int a,int b){ return fits[a]<fits[b]; });

        vector<Circuit> next; next.reserve(POP_SIZE);
        for(int i=0;i<mu;++i) next.push_back(pop[idx[i]]);

        while((int)next.size()<POP_SIZE){
            int pidx = idx[rint(0,mu-1)];
            Circuit child = pop[pidx];
            child = random_mutation(child);
            child = prune_inactive(child);
            next.push_back(move(child));
        }
        pop.swap(next);

        if(gen%1==0){
            ErrorStats es; fitness(best,&es);
            cerr<<"[Gen "<<gen<<"] best_fit="<< best_fit << " eps_th=" <<eps_th
                <<" nodes="<<best.nodes.size()
                <<" NMED="<<es.NMED<<" ER="<<es.ER<<" WCE="<<es.WCE
                <<" MRE="<<es.MRE<<" sMAPE="<<es.sMAPE<<std::endl;

            log_progress_txt(gen, best_fit, best, es, logfile);
        }
        if(gen%10==0){
            dump_netlist(best, std::string(OUTPUT_DIR) + "/netlist_output.txt");
        }
    }
    return {best_fit,best};
}

// ===================== MAIN (with CLI) =====================
int main(int argc, char** argv){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Simple CLI parsing: support --key=value or --key value
    auto get_val = [&](const std::string& arg, const std::string& key)->std::string {
        if(arg.rfind(key+"=", 0) == 0) return arg.substr(key.size()+1);
        return std::string();
    };

    bool logfile_was_set = false;
    for(int ai=1; ai<argc; ++ai){
        std::string a = argv[ai];
        if(a=="-h" || a=="--help"){
            std::cerr << "Usage: main_exec [options]\n"
                      << "  --netlist-file PATH\n"
                      << "  --logfile PATH\n"
                      << "  --generations N\n"
                      << "  --pop-size N\n"
                      << "  --top-k-ratio R\n"
                      << "  --eps-start V --eps-end V --eps-tau V\n"
                      << "  --seed N\n"
                      << "  --load-from-file 0|1\n"
                      << "  --signed-mult 0|1\n"
                      << "  --mut-weights v1,v2,v3,v4,v5,v6\n";
            return 0;
        }

        std::string v;
        if((v = get_val(a, "--netlist-file"))!="") NETLIST_FILE = v;
        else if((v = get_val(a, "--logfile"))!=""){ logfile = v; logfile_was_set = true; }
        else if((v = get_val(a, "--output-dir"))!=""){ OUTPUT_DIR = v; if(!logfile_was_set) logfile = std::string(OUTPUT_DIR) + "/evolution_metrics_signed8x8.txt"; }
        else if((v = get_val(a, "--generations"))!="") GENERATIONS = std::stoi(v);
        else if((v = get_val(a, "--pop-size"))!="") POP_SIZE = std::stoi(v);
        else if((v = get_val(a, "--top-k-ratio"))!="") TOP_K_RATIO = std::stod(v);
        else if((v = get_val(a, "--eps-start"))!="") EPS_START = std::stod(v);
        else if((v = get_val(a, "--eps-end"))!="") EPS_END = std::stod(v);
        else if((v = get_val(a, "--eps-tau"))!="") EPS_TAU = std::stod(v);
        else if((v = get_val(a, "--seed"))!="") SEED = (uint32_t)std::stoul(v);
        else if((v = get_val(a, "--load-from-file"))!="") LOAD_FROM_FILE = !(v=="0" || v=="false");
        else if((v = get_val(a, "--signed-mult"))!="") SIGNED_MULT = !(v=="0" || v=="false");
        else if((v = get_val(a, "--mut-weights"))!=""){
            // parse comma-separated 6 values
            std::vector<double> vals;
            size_t pos = 0;
            while(pos < v.size()){
                size_t comma = v.find(',', pos);
                std::string part = (comma==std::string::npos) ? v.substr(pos) : v.substr(pos, comma-pos);
                try{ vals.push_back(std::stod(part)); } catch(...) { vals.clear(); break; }
                if(comma==std::string::npos) break; else pos = comma+1;
            }
            if(vals.size()==6) for(int k=0;k<6;++k) MUT_WEIGHTS[k]=vals[k];
            else std::cerr<<"[Main] --mut-weights requires 6 comma-separated numbers\n";
        }
        else{
            // support space-separated form e.g. --netlist-file path
            if(a.rfind("--",0)==0 && ai+1<argc){
                std::string key = a;
                std::string val = argv[++ai];
                if(key=="--netlist-file") NETLIST_FILE = val;
                else if(key=="--logfile") { logfile = val; logfile_was_set = true; }
                else if(key=="--output-dir") { OUTPUT_DIR = val; if(!logfile_was_set) logfile = std::string(OUTPUT_DIR) + "/evolution_metrics_signed8x8.txt"; }
                else if(key=="--generations") GENERATIONS = std::stoi(val);
                else if(key=="--pop-size") POP_SIZE = std::stoi(val);
                else if(key=="--top-k-ratio") TOP_K_RATIO = std::stod(val);
                else if(key=="--eps-start") EPS_START = std::stod(val);
                else if(key=="--eps-end") EPS_END = std::stod(val);
                else if(key=="--eps-tau") EPS_TAU = std::stod(val);
                else if(key=="--seed") SEED = (uint32_t)std::stoul(val);
                else if(key=="--load-from-file") LOAD_FROM_FILE = !(val=="0" || val=="false");
                else if(key=="--signed-mult") SIGNED_MULT = !(val=="0" || val=="false");
                else if(key=="--mut-weights"){
                    std::vector<double> vals; size_t pos=0; std::string vv=val;
                    while(pos < vv.size()){
                        size_t comma = vv.find(',', pos);
                        std::string part = (comma==std::string::npos) ? vv.substr(pos) : vv.substr(pos, comma-pos);
                        try{ vals.push_back(std::stod(part)); } catch(...) { vals.clear(); break; }
                        if(comma==std::string::npos) break; else pos = comma+1;
                    }
                    if(vals.size()==6) for(int k=0;k<6;++k) MUT_WEIGHTS[k]=vals[k];
                    else std::cerr<<"[Main] --mut-weights requires 6 comma-separated numbers\n";
                }
                else{
                    std::cerr<<"[Main] Unknown option: "<<key<<"\n";
                }
            } else {
                std::cerr<<"[Main] Unknown argument: "<<a<<"\n";
            }
        }
    }

    // seed RNG after parsing user-supplied seed
    rng.seed(SEED);

    // ensure output directory exists
    try{
        std::filesystem::create_directories(OUTPUT_DIR);
    }catch(const std::exception& e){
        std::cerr<<"[Main] Warning: failed to create output dir '"<<OUTPUT_DIR<<"': "<<e.what()<<"\n";
    }

    // Build problem (signed/unsigned) after configuration parsing
    if(SIGNED_MULT){
        Problem signed_problem = build_problem_signed();
        ALL_INPUTS = signed_problem.inputs;
        ALL_TARGETS = signed_problem.targets;
        MAX_TRUE_ABS = signed_problem.max_true_abs;
    } else{
        Problem unsigned_problem = build_problem_unsigned();
        ALL_INPUTS = unsigned_problem.inputs;
        ALL_TARGETS = unsigned_problem.targets;
        MAX_TRUE_ABS = unsigned_problem.max_true_abs;
    }

    Circuit seed;
    if(LOAD_FROM_FILE){
        if(!load_verilog(NETLIST_FILE, seed)){
            cerr<<"[Main] Load failed, start from random.\n";
            seed = random_initial_circuit();
        }else{
            cerr<<"[Main] Loaded seed. nodes="<<seed.nodes.size()<<std::endl;
        }
    }else{
        cerr<<"[Main] Start from random seed.\n";
        seed = random_initial_circuit();
    }

    // normalize mutation weights
    double ws=accumulate(MUT_WEIGHTS.begin(),MUT_WEIGHTS.end(),0.0);
    if(ws>0) for(auto& w:MUT_WEIGHTS) w/=ws;

    auto res = evolve(seed);
    double best_fit = res.first;
    Circuit best = res.second;

    ErrorStats es; fitness(best,&es);
    cout << "\nBest fitness: " << best_fit << std::endl;
    cout << "Nodes: " << best.nodes.size() << std::endl;
    cout << "NMED=" << es.NMED << "  ER=" << es.ER << "  WCE=" << es.WCE
         << "  MRE=" << es.MRE << "  sMAPE=" << es.sMAPE << std::endl;

    dump_netlist(best, std::string(OUTPUT_DIR) + "/netlist_output.txt");
    return 0;
}
