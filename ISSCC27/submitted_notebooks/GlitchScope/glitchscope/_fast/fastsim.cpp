// GlitchScope compiled pulse simulator (M0 / M1 / M2, ideal-cell interventions).
//
// A port of PulseSimulator._run_once / run (glitchscope/sim.py) that keeps the same
// event ids, sequence numbers, tie-breaking, integer femtosecond arithmetic and
// round-half-even conversions, so traces are event-for-event identical to the Python
// engine.  M2 re-simulation follows the same schedule: with rollback, resume from the
// latest checkpoint before the earliest affected cause time and stop an attempt at the
// first time step that reports a violation; without, restart from t = 0 (reference).
//
// Liberty arc selection (when-conditions, timing sense) and cell functions are
// precomputed in Python into lookup tables; this file interpolates the selected
// NLDM tables with the same operation order as liberty.bilinear.
// Build: g++ -O2 -ffp-contract=off -shared -fPIC fastsim.cpp -o libgsfast.so
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <map>
#include <queue>
#include <set>
#include <tuple>
#include <vector>

typedef long long i64;

namespace {

struct Sched {
  i64 time, seq; int eid, net, val, cell;
  bool operator>(const Sched& o) const { return time != o.time ? time > o.time : seq > o.seq; }
};
struct Pend {
  int eid; i64 time; int value; i64 cause, delay, R, slew; int epoch;
  std::vector<int> parents; bool doomed = false;
};
struct Trace { int eid; i64 time; int epoch, net, oldv, newv, cell; std::vector<int> parents; };
struct Sup {
  int cell, epoch, lead_value; i64 cause, cancel, delay, R, slew; int reason, lead_pin;
  std::vector<int> lead_parents, cancel_parents;
};
struct Meta { i64 cause, delay, slew_in, slew_out, R; int pin, multi; };
typedef std::tuple<int, i64, int> Key;   // (cell, time, value)

struct Model {
  int n_nets = 0, n_cells = 0, model = 0;   // model: 0 M0, 1 M1, 2 M2
  std::vector<int> cell_out, in_off, in_net, pin_rank, truth_off, topo_index, cell_rank, net_rank, fan_off,
      fan_cell, arc_off, arc, tab_n1, tab_n2, tab_off, topo_order;
  std::vector<uint8_t> truth, rcal;
  std::vector<double> load, tab_data, rab;
  std::vector<double> dscale;   // optional per-cell delay/slew factor (local variation); empty = 1
  std::vector<double> talpha;   // M2 trailing-edge slew coefficient per (cell, pulse polarity); empty = 0
  std::vector<i64> pi_slew;
  double tu_ps = 1, cu_ff = 1, clamp_lo = 0.3, clamp_hi = 2.5;
  // per-run outputs
  std::vector<Trace> trace; std::vector<Sup> sup; std::vector<Meta> meta; std::vector<uint8_t> has_meta;
  std::vector<uint8_t> final_v; std::vector<int> rcalls; int reruns = 0;
};

inline void bracket(const double* xs, int n, double x, int& i0, int& i1, double& xc) {
  if (x <= xs[0]) { i0 = 0; i1 = 1; xc = xs[0]; return; }
  if (x >= xs[n - 1]) { i0 = n - 2; i1 = n - 1; xc = xs[n - 1]; return; }
  for (int i = 0; i < n - 1; i++)
    if (xs[i] <= x && x <= xs[i + 1]) { i0 = i; i1 = i + 1; xc = x; return; }
  i0 = 0; i1 = 1; xc = xs[0];
}

inline double bilinear(const Model& m, int t, double x, double y) {
  const int n1 = m.tab_n1[t], n2 = m.tab_n2[t];
  const double* i1 = &m.tab_data[m.tab_off[t]];
  const double* i2 = i1 + n1;
  const double* v = i2 + n2;
  int a0, a1, b0, b1; double xc, yc;
  bracket(i1, n1, x, a0, a1, xc);
  bracket(i2, n2, y, b0, b1, yc);
  const double x0 = i1[a0], x1 = i1[a1], y0 = i2[b0], y1 = i2[b1];
  const double tx = (x1 == x0) ? 0.0 : (xc - x0) / (x1 - x0);
  const double ty = (y1 == y0) ? 0.0 : (yc - y0) / (y1 - y0);
  const double q00 = v[a0 * n2 + b0], q01 = v[a0 * n2 + b1], q10 = v[a1 * n2 + b0], q11 = v[a1 * n2 + b1];
  return (q00 * (1 - ty) + q01 * ty) * (1 - tx) + (q10 * (1 - ty) + q11 * ty) * tx;
}

inline i64 ps_to_fs(double ps) { return (i64)std::nearbyint(ps * 1000.0); }

inline int in_bits(const Model& m, int c, const std::vector<uint8_t>& phys) {
  int idx = 0;
  for (int j = m.in_off[c], b = 0; j < m.in_off[c + 1]; j++, b++) idx |= (phys[m.in_net[j]] & 1) << b;
  return idx;
}
inline int eval_cell(const Model& m, int c, const std::vector<uint8_t>& phys) {
  return m.truth[m.truth_off[c] + in_bits(m, c, phys)];
}
inline void eval_stable(const Model& m, std::vector<uint8_t>& phys) {
  for (int c : m.topo_order) phys[m.cell_out[c]] = (uint8_t)eval_cell(m, c, phys);
}

enum { R_ROLLBACK = 0, R_M1 = 1, R_M2 = 2, R_NONPOS = 3 };
enum { OK = 0, E_CYCLE = 1, E_NOCONV = 2, E_MISMATCH = 3, E_CAUSAL = 4, E_NOARC = 5 };

struct Epochs {
  std::vector<i64> time; std::vector<int> id;
  std::vector<std::vector<std::pair<int, int>>> upd;
};

struct Run {
  Model& m; const std::set<Key>& reject; const std::vector<uint8_t>& ideal; const std::vector<uint8_t>& final_state;
  bool any_ideal;
  std::vector<uint8_t> phys, logical, has_fired, canceled;
  std::vector<std::vector<Pend>> pending;
  std::vector<std::tuple<i64, int, i64, i64, i64>> last_fired;
  std::vector<Trace> trace; std::vector<Sup> sup;
  std::vector<Meta> meta; std::vector<uint8_t> has_meta;
  std::vector<int> trace_of; std::vector<i64> eslew;
  std::vector<std::tuple<int, i64, int, i64>> violations;   // cell, fire time, value, detect time
  std::priority_queue<Sched, std::vector<Sched>, std::greater<Sched>> q;
  int eid = 1, npend = 0, error = OK; i64 seq = 1;
  // rollback bookkeeping (mirrors sim.py with rollback=True)
  bool track = false; int K = 32;
  std::vector<int> cancel_log;            // eid of every suppressed record, parallel to sup
  std::map<Key, i64> first_cause;
  std::vector<std::pair<Key, i64>> fc_log;   // insertion order = non-decreasing time
  struct Snap {
    i64 T; long step; size_t i; std::vector<uint8_t> phys, logical, has_fired;
    std::vector<std::pair<int, std::vector<Pend>>> pending;
    std::vector<std::tuple<i64, int, i64, i64, i64>> last_fired;
    size_t ntrace, nsup; int eid; i64 seq; int npend;
    std::priority_queue<Sched, std::vector<Sched>, std::greater<Sched>> q;
  };
  std::vector<Snap> snaps;
  size_t i = 0; long step = 0; bool completed = false;

  Run(Model& m_, const std::set<Key>& r, const std::vector<uint8_t>& id, const std::vector<uint8_t>& fs, bool ai)
      : m(m_), reject(r), ideal(id), final_state(fs), any_ideal(ai) {}

  int new_eid() {
    int e = eid++;
    if ((size_t)e >= trace_of.size()) {
      size_t n = std::max<size_t>(1024, 2 * (size_t)e);
      trace_of.resize(n, -1); eslew.resize(n, 0); canceled.resize(n, 0); meta.resize(n); has_meta.resize(n, 0);
    }
    return e;
  }

  void record_cancel(int c, const Pend& p, i64 t, int reason, const std::vector<int>& cparents) {
    canceled[p.eid] = 1;
    cancel_log.push_back(p.eid);
    Sup s;
    s.cell = c; s.epoch = p.epoch; s.lead_value = p.value; s.cause = p.cause; s.cancel = t; s.delay = p.delay;
    s.R = p.R; s.slew = p.slew; s.reason = reason; s.lead_parents = p.parents; s.cancel_parents = cparents;
    std::sort(s.cancel_parents.begin(), s.cancel_parents.end());
    s.lead_pin = has_meta[p.eid] ? meta[p.eid].pin : -1;
    sup.push_back(std::move(s));
  }

  i64 reject_fs(int c, int newv, i64 slew, i64 delay) {
    if (m.model == 0) return 0;
    if (m.model == 1) return delay;
    const int pol = newv ? 0 : 1;
    m.rcalls[2 * c + pol]++;
    if (!m.rcal[2 * c + pol]) return (i64)std::nearbyint(1.0 * (double)delay);
    const double x = delay > 0 ? (double)slew / (double)delay : 0.0;
    double r = m.rab[4 * c + 2 * pol] + m.rab[4 * c + 2 * pol + 1] * x;
    r = std::min(m.clamp_hi, std::max(m.clamp_lo, r));
    return (i64)std::nearbyint(r * (double)delay);
  }

  void schedule_cell(int c, i64 t, std::vector<int>& parent_ids, const std::vector<int>& changed) {
    const int newv = eval_cell(m, c, phys);
    auto& plist = pending[c];
    const int out = m.cell_out[c];
    if (ideal[c]) {
      const int tgt = final_state[out];
      logical[c] = (uint8_t)newv;
      if (newv != tgt || phys[out] == tgt || !plist.empty()) return;
    } else if (newv == logical[c]) {
      return;
    }
    logical[c] = (uint8_t)newv;
    const bool use_ta = m.model == 2 && !m.talpha.empty();
    i64 s_tr = 0;
    if (use_ta)
      for (int pid : parent_ids) s_tr = std::max(s_tr, eslew[pid]);
    if (!plist.empty()) {
      const Pend& last = plist.back();
      i64 w = t - last.cause;
      if (use_ta) {
        const double a = m.talpha[2 * c + (last.value ? 0 : 1)];
        if (a != 0.0) w -= (i64)(a * (double)(s_tr - last.slew));
      }
      if (last.doomed || m.model == 1 || w < last.R) {
        Pend l = std::move(plist.back()); plist.pop_back(); npend--;
        record_cancel(c, l, t, l.doomed ? R_ROLLBACK : (m.model == 1 ? R_M1 : R_M2), parent_ids);
        const int cmp = plist.empty() ? phys[out] : plist.back().value;
        if (newv == cmp) return;
      }
    } else if (m.model == 2 && has_fired[c] && !ideal[c]) {
      const auto& lf = last_fired[c];
      i64 wv = t - std::get<2>(lf);
      if (use_ta) {
        const double a = m.talpha[2 * c + (std::get<1>(lf) ? 0 : 1)];
        if (a != 0.0) wv -= (i64)(a * (double)(s_tr - std::get<4>(lf)));
      }
      if (std::get<1>(lf) == phys[out] && std::get<1>(lf) != newv && wv < std::get<3>(lf))
        violations.emplace_back(c, std::get<0>(lf), std::get<1>(lf), t);
    }
    // choose_arc: candidates over changed input pins, min (delay, pin name)
    const int bits = in_bits(m, c, phys);
    const int k = m.in_off[c + 1] - m.in_off[c];
    bool found = false; int nc = 0;
    i64 bd = 0, bslew = 0, boslew = 0; int brank = 0, bpin = 0, bpev = -1;
    for (int j = 0; j < k; j++) {
      const int n = m.in_net[m.in_off[c] + j];
      if (std::find(changed.begin(), changed.end(), n) == changed.end()) continue;
      int pev = -1, cnt = 0;
      for (int pid : parent_ids) {
        const int ti = trace_of[pid];
        if (ti >= 0 && trace[ti].net == n) { pev = ti; cnt++; }
      }
      if (cnt != 1) { error = E_CAUSAL; return; }
      const Trace& ev = trace[pev];
      const int idx = m.arc_off[c] + ((((j * 2 + newv) * 2 + ev.oldv) << k) + bits);
      const int dt = m.arc[2 * idx], st = m.arc[2 * idx + 1];
      if (dt < 0) continue;
      const i64 slew = eslew[ev.eid];
      const double x = ((double)slew / 1000.0) / m.tu_ps;
      const double y = m.load[out] / m.cu_ff;
      i64 d = ps_to_fs(bilinear(m, dt, x, y) * m.tu_ps);
      i64 so = ps_to_fs(bilinear(m, st, x, y) * m.tu_ps);
      if (!m.dscale.empty()) {
        d = (i64)std::floor((double)d * m.dscale[c] + 0.5);
        so = (i64)std::floor((double)so * m.dscale[c] + 0.5);
      }
      const int rank = m.pin_rank[m.in_off[c] + j];
      nc++;
      if (!found || d < bd || (d == bd && rank < brank)) {
        found = true; bd = d; brank = rank; bpin = j; bpev = pev; bslew = slew; boslew = so;
      }
    }
    if (!found) { error = E_NOARC; return; }
    const int my = new_eid();
    const i64 ev_time = t + bd;
    if (!plist.empty() && ev_time <= plist.back().time) {
      Pend prev = std::move(plist.back()); plist.pop_back(); npend--;
      record_cancel(c, prev, t, R_NONPOS, parent_ids);
      return;
    }
    const i64 R = reject_fs(c, newv, bslew, bd);
    Pend p;
    p.eid = my; p.time = ev_time; p.value = newv; p.cause = t; p.delay = bd; p.R = R; p.slew = bslew;
    p.epoch = trace[bpev].epoch; p.parents = parent_ids;
    std::sort(p.parents.begin(), p.parents.end());
    meta[my] = Meta{t, bd, bslew, boslew, R, bpin, nc > 1 ? 1 : 0}; has_meta[my] = 1;
    if (track && first_cause.emplace(Key(c, ev_time, newv), t).second) fc_log.emplace_back(Key(c, ev_time, newv), t);
    if (reject.count(Key(c, ev_time, newv))) p.doomed = true;
    else { q.push(Sched{ev_time, seq, my, out, newv, c}); seq++; }
    eslew[my] = boslew;
    plist.push_back(std::move(p)); npend++;
  }

  void fan(const std::vector<int>& actual, i64 t) {
    // topo index -> (cell, parent event ids, changed nets)
    std::map<int, std::tuple<int, std::vector<int>, std::vector<int>>> aff;
    for (int ti : actual) {
      const Trace& ev = trace[ti];
      for (int f = m.fan_off[ev.net]; f < m.fan_off[ev.net + 1]; f++) {
        const int c = m.fan_cell[f];
        auto& e = aff[m.topo_index[c]];
        std::get<0>(e) = c;
        auto& ps = std::get<1>(e); auto& ns = std::get<2>(e);
        if (std::find(ps.begin(), ps.end(), ev.eid) == ps.end()) ps.push_back(ev.eid);
        if (std::find(ns.begin(), ns.end(), ev.net) == ns.end()) ns.push_back(ev.net);
      }
    }
    for (auto& kv : aff) {
      schedule_cell(std::get<0>(kv.second), t, std::get<1>(kv.second), std::get<2>(kv.second));
      if (error) return;
    }
  }

  bool stable() const {
    std::vector<uint8_t> e = phys;
    eval_stable(m, e);
    return e == phys;
  }

  int append_trace(Trace&& te) {
    trace_of[te.eid] = (int)trace.size();
    trace.push_back(std::move(te));
    return (int)trace.size() - 1;
  }

  void fresh(const std::vector<uint8_t>& init) {
    phys = init; eval_stable(m, phys);
    logical.assign(m.n_cells, 0);
    for (int c = 0; c < m.n_cells; c++) logical[c] = phys[m.cell_out[c]];
    pending.assign(m.n_cells, {}); last_fired.assign(m.n_cells, {}); has_fired.assign(m.n_cells, 0);
    trace.clear(); sup.clear(); cancel_log.clear(); first_cause.clear(); fc_log.clear();
    std::fill(trace_of.begin(), trace_of.end(), -1);
    std::fill(canceled.begin(), canceled.end(), 0);
    std::fill(has_meta.begin(), has_meta.end(), 0);
    q = decltype(q)();
    eid = 1; seq = 1; npend = 0; i = 0; step = 0;
  }

  void snapshot(i64 T) {
    Snap sn;
    sn.T = T; sn.step = step; sn.i = i; sn.phys = phys; sn.logical = logical; sn.has_fired = has_fired;
    for (int c = 0; c < m.n_cells; c++) if (!pending[c].empty()) sn.pending.emplace_back(c, pending[c]);
    sn.last_fired = last_fired; sn.ntrace = trace.size(); sn.nsup = sup.size();
    sn.eid = eid; sn.seq = seq; sn.npend = npend; sn.q = q;
    snaps.push_back(std::move(sn));
  }

  void restore(const Snap& sn) {
    phys = sn.phys; logical = sn.logical; has_fired = sn.has_fired; last_fired = sn.last_fired;
    for (auto& pl : pending) pl.clear();
    for (auto& kv : sn.pending) pending[kv.first] = kv.second;
    for (size_t k = sn.ntrace; k < trace.size(); k++) trace_of[trace[k].eid] = -1;
    trace.resize(sn.ntrace);
    for (size_t k = sn.nsup; k < cancel_log.size(); k++) canceled[cancel_log[k]] = 0;
    sup.resize(sn.nsup); cancel_log.resize(sn.nsup);
    for (int e = sn.eid; e < eid && (size_t)e < trace_of.size(); e++) { trace_of[e] = -1; canceled[e] = 0; has_meta[e] = 0; }
    while (!fc_log.empty() && fc_log.back().second >= sn.T) {     // O(entries undone)
      first_cause.erase(fc_log.back().first); fc_log.pop_back();
    }
    q = sn.q; eid = sn.eid; seq = sn.seq; npend = sn.npend; i = sn.i; step = sn.step;
  }

  // One attempt.  With tracking, resume from the latest checkpoint before t_change
  // (has_tc) or from t = 0, and stop after the first time step that reports a violation.
  int attempt(const Epochs& ep, const std::vector<uint8_t>& init, bool has_tc, i64 tc) {
    violations.clear(); error = OK; completed = false;
    if (track && has_tc) { while (!snaps.empty() && snaps.back().T >= tc) snaps.pop_back(); }
    else snaps.clear();
    if (!snaps.empty()) restore(snaps.back()); else fresh(init);
    while (i < ep.time.size() || !q.empty()) {
      while (!q.empty() && canceled[q.top().eid]) q.pop();
      if (i >= ep.time.size() && q.empty()) break;
      const bool hq = !q.empty();
      const i64 nt = hq ? q.top().time : 0;
      const bool is_epoch = i < ep.time.size() && (!hq || ep.time[i] <= nt);
      if (track && step % K == 0 && (snaps.empty() || snaps.back().step < step)) snapshot(is_epoch ? ep.time[i] : nt);
      step++;
      std::vector<int> act;
      if (is_epoch) {
        const i64 t = ep.time[i];
        for (const auto& u : ep.upd[i]) {
          const int n = u.first, nv = u.second;
          if (phys[n] != nv) {
            const int my = new_eid();
            Trace te{my, t, ep.id[i], n, phys[n], nv, -1, {}};
            phys[n] = (uint8_t)nv;
            eslew[my] = m.pi_slew[n];
            act.push_back(append_trace(std::move(te)));
          }
        }
        i++;
        fan(act, t);
      } else {
        std::vector<Sched> batch;
        while (!q.empty() && q.top().time == nt) {
          Sched e = q.top(); q.pop();
          if (!canceled[e.eid]) batch.push_back(e);
        }
        std::sort(batch.begin(), batch.end(), [&](const Sched& a, const Sched& b) {
          const int ra = m.net_rank[a.net], rb = m.net_rank[b.net];
          if (ra != rb) return ra < rb;
          if (a.seq != b.seq) return a.seq < b.seq;
          return a.eid < b.eid;
        });
        for (const auto& e : batch) {
          auto& plist = pending[e.cell];
          size_t pi = 0;
          while (pi < plist.size() && plist[pi].eid != e.eid) pi++;
          Pend p = std::move(plist[pi]);
          plist.erase(plist.begin() + pi); npend--;
          const int cur = phys[e.net];
          if (e.val != cur) {
            Trace te{e.eid, e.time, p.epoch, e.net, cur, e.val, e.cell, p.parents};
            phys[e.net] = (uint8_t)e.val;
            last_fired[e.cell] = std::make_tuple(e.time, e.val, p.cause, p.R, p.slew); has_fired[e.cell] = 1;
            act.push_back(append_trace(std::move(te)));
          }
        }
        fan(act, nt);
      }
      if (error) return error;
      if (npend == 0 && !any_ideal && !stable()) return E_MISMATCH;
      if (track && !violations.empty()) return OK;
    }
    completed = true;
    return OK;
  }
};

}  // namespace

extern "C" {

void* gs_create(int n_nets, int n_cells, int model, const int* cell_out, const int* in_off, const int* in_net,
                const int* pin_rank, const uint8_t* truth, const int* truth_off, int truth_len,
                const int* topo_index, const int* cell_rank, const int* net_rank, const int* fan_off,
                const int* fan_cell, const double* load, const int* arc_off, const int* arc, int arc_len, int n_tab,
                const int* tab_n1, const int* tab_n2, const int* tab_off, const double* tab_data, int data_len,
                double tu_ps, double cu_ff, const double* rab, const uint8_t* rcal, double clamp_lo, double clamp_hi,
                const long long* pi_slew) {
  Model* m = new Model();
  m->n_nets = n_nets; m->n_cells = n_cells; m->model = model;
  m->cell_out.assign(cell_out, cell_out + n_cells);
  m->in_off.assign(in_off, in_off + n_cells + 1);
  m->in_net.assign(in_net, in_net + in_off[n_cells]);
  m->pin_rank.assign(pin_rank, pin_rank + in_off[n_cells]);
  m->truth.assign(truth, truth + truth_len);
  m->truth_off.assign(truth_off, truth_off + n_cells);
  m->topo_index.assign(topo_index, topo_index + n_cells);
  m->cell_rank.assign(cell_rank, cell_rank + n_cells);
  m->net_rank.assign(net_rank, net_rank + n_nets);
  m->fan_off.assign(fan_off, fan_off + n_nets + 1);
  m->fan_cell.assign(fan_cell, fan_cell + fan_off[n_nets]);
  m->load.assign(load, load + n_nets);
  m->arc_off.assign(arc_off, arc_off + n_cells);
  m->arc.assign(arc, arc + arc_len);
  m->tab_n1.assign(tab_n1, tab_n1 + n_tab);
  m->tab_n2.assign(tab_n2, tab_n2 + n_tab);
  m->tab_off.assign(tab_off, tab_off + n_tab);
  m->tab_data.assign(tab_data, tab_data + data_len);
  m->tu_ps = tu_ps; m->cu_ff = cu_ff; m->clamp_lo = clamp_lo; m->clamp_hi = clamp_hi;
  m->rab.assign(rab, rab + 4 * n_cells);
  m->rcal.assign(rcal, rcal + 2 * n_cells);
  m->pi_slew.assign(pi_slew, pi_slew + n_nets);
  m->rcalls.assign(2 * n_cells, 0);
  std::vector<std::pair<int, int>> order;
  for (int c = 0; c < n_cells; c++) order.push_back({topo_index[c], c});
  std::sort(order.begin(), order.end());
  for (auto& p : order) m->topo_order.push_back(p.second);
  return m;
}

void gs_free(void* h) { delete (Model*)h; }

// per-cell delay/slew factors (n = 0 clears them)
void gs_set_talpha(void* h, int n, const double* s) {
  Model& m = *(Model*)h;
  if (n <= 0) m.talpha.clear(); else m.talpha.assign(s, s + n);
}

void gs_set_scale(void* h, int n, const double* s) {
  Model& m = *(Model*)h;
  if (n <= 0) m.dscale.clear(); else m.dscale.assign(s, s + n);
}

int gs_run(void* h, int n_ep, const long long* ep_time, const int* ep_id, const int* ep_off, const int* ep_net,
           const int* ep_val, const uint8_t* init, const uint8_t* ideal_flags, int max_reruns, int rollback,
           int checkpoint_every) {
  Model& m = *(Model*)h;
  Epochs ep;
  ep.time.assign(ep_time, ep_time + n_ep);
  ep.id.assign(ep_id, ep_id + n_ep);
  ep.upd.resize(n_ep);
  for (int i = 0; i < n_ep; i++)
    for (int j = ep_off[i]; j < ep_off[i + 1]; j++) ep.upd[i].push_back({ep_net[j], ep_val[j]});
  std::vector<uint8_t> initv(init, init + m.n_nets), ideal(ideal_flags, ideal_flags + m.n_cells);
  bool any_ideal = false;
  for (auto f : ideal) any_ideal = any_ideal || f;
  std::vector<uint8_t> final_state(m.n_nets, 0);
  if (any_ideal) {
    final_state = initv;
    for (auto& u : ep.upd) for (auto& x : u) final_state[x.first] = (uint8_t)x.second;
    eval_stable(m, final_state);
  }
  std::set<Key> reject;
  std::set<std::set<Key>> seen;
  Run r(m, reject, ideal, final_state, any_ideal);
  r.track = m.model == 2 && rollback; r.K = std::max(1, checkpoint_every);
  bool has_tc = false; i64 tc = 0;
  for (int attempt = 0; attempt <= max_reruns; attempt++) {
    const int rc = r.attempt(ep, initv, has_tc, tc);
    if (rc) return rc;
    std::vector<Key> stale;
    if (r.completed)
      for (int c = 0; c < m.n_cells; c++)
        for (auto& p : r.pending[c]) if (p.doomed) stale.emplace_back(c, p.time, p.value);
    std::vector<i64> change;
    if (!stale.empty()) {
      for (auto& s : stale) {
        reject.erase(s);
        auto it = r.first_cause.find(s);
        if (it != r.first_cause.end()) change.push_back(it->second);
      }
    } else if (r.violations.empty()) {
      if (r.npend) return E_MISMATCH;
      if (!r.stable()) return E_MISMATCH;
      m.trace = std::move(r.trace); m.sup = std::move(r.sup);
      m.meta = std::move(r.meta); m.has_meta = std::move(r.has_meta);
      m.final_v = r.phys; m.reruns = attempt;
      return OK;
    } else {
      // Python: min(violations, key=(detect time, fire time, cell name))
      auto key = [&](const std::tuple<int, i64, int, i64>& v) {
        return std::make_tuple(std::get<3>(v), std::get<1>(v), m.cell_rank[std::get<0>(v)]);
      };
      auto best = r.violations[0];
      for (auto& v : r.violations) if (key(v) < key(best)) best = v;
      const Key k(std::get<0>(best), std::get<1>(best), std::get<2>(best));
      reject.insert(k);
      auto it = r.first_cause.find(k);
      if (it != r.first_cause.end()) change.push_back(it->second);
    }
    has_tc = !change.empty();
    tc = has_tc ? *std::min_element(change.begin(), change.end()) : 0;
    if (seen.count(reject)) return E_CYCLE;
    seen.insert(reject);
  }
  return E_NOCONV;
}

int gs_n_trace(void* h) { return (int)((Model*)h)->trace.size(); }
int gs_n_sup(void* h) { return (int)((Model*)h)->sup.size(); }
int gs_reruns(void* h) { return ((Model*)h)->reruns; }
int gs_n_trace_parents(void* h) {
  int n = 0;
  for (auto& t : ((Model*)h)->trace) n += (int)t.parents.size();
  return n;
}
// total lead-parent and cancel-parent counts
void gs_n_sup_parents(void* h, int* out) {
  int a = 0, b = 0;
  for (auto& s : ((Model*)h)->sup) { a += (int)s.lead_parents.size(); b += (int)s.cancel_parents.size(); }
  out[0] = a; out[1] = b;
}

// trace rows + meta (meta valid where m_has = 1)
void gs_get_trace(void* h, int* eid, long long* time, int* epoch, int* net, int* oldv, int* newv, int* cell,
                  int* par_off, int* par, long long* m_cause, long long* m_delay, long long* m_slew_in,
                  long long* m_slew_out, long long* m_R, int* m_pin, int* m_multi, int* m_has) {
  Model& m = *(Model*)h;
  int np = 0;
  for (size_t i = 0; i < m.trace.size(); i++) {
    const Trace& t = m.trace[i];
    eid[i] = t.eid; time[i] = t.time; epoch[i] = t.epoch; net[i] = t.net; oldv[i] = t.oldv; newv[i] = t.newv;
    cell[i] = t.cell; par_off[i] = np;
    for (int p : t.parents) par[np++] = p;
    const bool hm = (size_t)t.eid < m.has_meta.size() && m.has_meta[t.eid];
    m_has[i] = hm;
    if (hm) {
      const Meta& x = m.meta[t.eid];
      m_cause[i] = x.cause; m_delay[i] = x.delay; m_slew_in[i] = x.slew_in; m_slew_out[i] = x.slew_out;
      m_R[i] = x.R; m_pin[i] = x.pin; m_multi[i] = x.multi;
    }
  }
  par_off[m.trace.size()] = np;
}

void gs_get_sup(void* h, int* cell, int* epoch, int* lead_value, long long* cause, long long* cancel,
                long long* delay, long long* R, long long* slew, int* reason, int* lead_pin, int* lp_off, int* lp,
                int* cp_off, int* cp) {
  Model& m = *(Model*)h;
  int a = 0, b = 0;
  for (size_t i = 0; i < m.sup.size(); i++) {
    const Sup& s = m.sup[i];
    cell[i] = s.cell; epoch[i] = s.epoch; lead_value[i] = s.lead_value; cause[i] = s.cause; cancel[i] = s.cancel;
    delay[i] = s.delay; R[i] = s.R; slew[i] = s.slew; reason[i] = s.reason; lead_pin[i] = s.lead_pin;
    lp_off[i] = a; for (int p : s.lead_parents) lp[a++] = p;
    cp_off[i] = b; for (int p : s.cancel_parents) cp[b++] = p;
  }
  lp_off[m.sup.size()] = a; cp_off[m.sup.size()] = b;
}

void gs_get_final(void* h, uint8_t* out) {
  Model& m = *(Model*)h;
  std::memcpy(out, m.final_v.data(), m.final_v.size());
}

// r_filter calls per (cell, polarity) since the last read (for M2Model bookkeeping)
void gs_get_rcalls(void* h, int* out) {
  Model& m = *(Model*)h;
  for (int c = 0; c < 2 * m.n_cells; c++) { out[c] = m.rcalls[c]; m.rcalls[c] = 0; }
}

}  // extern "C"
