"""Independent steady supply/completion measurements for the folded LB pilot."""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
import re

import subprocess,time
def digest(path):
    return "sha256:"+hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2)+"\n")
def command(root,cmd,output,timeout=7200):
    output.parent.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    # Preserve simulator stdout/stderr and fail on timeout or nonzero status.
    with output.open("w") as log:
        result=subprocess.run([str(x) for x in cmd],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    save(output.with_suffix(".receipt.json"),dict(command=[str(x) for x in cmd],
        returncode=result.returncode,seconds=time.monotonic()-start,log_digest=digest(output)))
    result.check_returncode()



DECLARATIONS = r'''
  integer perf_seed,profile,stall_profile,service_cycle[0:1099],response_count[0:1099];
  integer qjob[0:9][0:3],last_due[0:9],burst_active[0:9];
  reg [9:0] ready_events[0:999999];
  reg [3:0] latency_events[0:175999];
  reg [4095:0] ready_file,latency_file;
'''

SERVICE = r'''
  always @(negedge clk) begin
    phy_rsp_valid=0;phy_rsp_error=0;phy_req_ready=0;
    out_ready=rst_n && (stall_profile==0 || cycles%11>=3);
    if(rst_n) for(integer p=0;p<10;p=p+1) begin
      phy_req_ready[p]=profile==1 ? ready_events[cycles][p] : 1;
      if(qcount[p]==0) burst_active[p]=0;
      if(qcount[p]>=4 || (qcount[p]>0 && cycles-qaddr[p][qhead[p]]>=16)) burst_active[p]=1;
      if(qcount[p]>0 && (profile==0 || (profile==1 && qaddr[p][qhead[p]]<=cycles+1) || (profile==2 && burst_active[p]))) begin
        phy_rsp_valid[p]=1;
        phy_rsp_rdata[p*32+:32]=qdata[p][qhead[p]];
        phy_rsp_error[p]=qerr[p][qhead[p]];
      end
    end
  end
'''

DRIVER = r'''
  initial begin
    unloaded=1; random_state=11; count=1100;
    tmp=$value$plusargs("perf_k=%d",active_k);
    tmp=$value$plusargs("perf_map=%d",code);
    tmp=$value$plusargs("perf_profile=%d",profile);
    tmp=$value$plusargs("perf_stall=%d",stall_profile);
    if(!$value$plusargs("vectors=%s",filename)) $fatal(1,"performance vectors missing");
    if(!$value$plusargs("ready_events=%s",ready_file)) $fatal(1,"ready events missing");
    if(!$value$plusargs("latency_events=%s",latency_file)) $fatal(1,"latency events missing");
    $readmemh(ready_file,ready_events); $readmemh(latency_file,latency_events);
    fd=$fopen(filename,"r"); if(fd==0) $fatal(1,"performance vectors unreadable");
    for(j=0;j<64;j=j+1) scan=$fscanf(fd,"%d",x[j]);
    for(j=0;j<64;j=j+1) for(lane=0;lane<8;lane=lane+1) begin scan=$fscanf(fd,"%d",tmp);w[j][lane]=tmp;end
    for(j=0;j<8;j=j+1) begin scan=$fscanf(fd,"%d",tmp);for(n=0;n<count;n=n+1) expected[n][j]=tmp;end
    for(n=0;n<count;n=n+1) begin
      expected_bank[n]=n%2;expected_error[n]=0;response_count[n]=0;service_cycle[n]=-1;
    end
    for(j=0;j<10;j=j+1) begin last_due[j]=0;burst_active[j]=0;end
    reset_dut();configure(code);
    for(slot=0;slot<2;slot=slot+1) for(word=0;word<8;word=word+1) begin
      @(negedge clk);in_valid=1;in_bank=slot;in_word=word;
      for(j=0;j<8;j=j+1) in_data[j*8+:8]=x[word*8+j][7:0];
      @(posedge clk);if(!in_ready)$fatal(1,"performance input preload rejected");
    end
    @(negedge clk);in_valid=0;cmd_valid=1;cmd_k=active_k;cmd_in_bank=0;cmd_out_bank=0;
    for(n=0;n<count;n=n+1) begin
      @(posedge clk);while(!cmd_ready)@(posedge clk);
      accepted_cycle[n]=cycles;tail=tail+1;
      @(negedge clk);cmd_in_bank=(n+1)%2;cmd_out_bank=(n+1)%2;
    end
    cmd_valid=0;
    while(head<count) @(negedge clk);
    for(j=0;j<10;j=j+1) if(phys_to_log[j]>=0 && issued[j]!=count*active_k/4) $fatal(1,"performance request count");
    for(n=0;n<count;n=n+1) if(response_count[n]!=8*active_k/4) $fatal(1,"performance service byte count");
    tmp=0;for(n=100;n<count;n=n+1) if(finish_cycle[n]-accepted_cycle[n]>tmp) tmp=finish_cycle[n]-accepted_cycle[n];
    $display("FOLD_PERF_PASS jobs=1100 intervals=1000 completion_cycles=%0d supply_cycles=%0d useful_bytes=%0d max_latency=%0d",
      finish_cycle[1099]-finish_cycle[99],service_cycle[1099]-service_cycle[99],1000*8*active_k,tmp);
    $finish;
  end
endmodule
'''


def testbench(original):
    marker = '  initial begin\n    tmp=$value$plusargs("seed=%d",seed);'
    service = '  always @(negedge clk) begin\n    phy_rsp_valid=0;'
    anchors = [marker, service, 'qaddr[p][qtail[p]]=cycles;', 'tile!=issued[p]',
               'qhead[p]=(qhead[p]+1)%4;qcount[p]=qcount[p]-1;']
    if any(original.count(a) != 1 for a in anchors):
        raise ValueError('independent checker extraction anchors changed')
    source = original.split(marker)[0].split(service)[0]
    source = source.replace('  lb_feedback dut(.*);', DECLARATIONS+'\n  lb_feedback dut(.*);')
    source = source.replace('always #5', 'always #50').replace('cycles>4000000', 'cycles>=1000000')
    source = source.replace('tile!=issued[p]', 'tile!=(issued[p]%(active_k/4))')
    source = source.replace('qaddr[p][qtail[p]]=cycles;', r'''
          qjob[p][qtail[p]]=issued[p]/(active_k/4);
          if(profile==1) begin
            qaddr[p][qtail[p]]=cycles+latency_events[p*17600+issued[p]];
            if(qaddr[p][qtail[p]]<=last_due[p]) qaddr[p][qtail[p]]=last_due[p]+1;
            last_due[p]=qaddr[p][qtail[p]];
          end else qaddr[p][qtail[p]]=cycles;
''')
    source = source.replace('qhead[p]=(qhead[p]+1)%4;qcount[p]=qcount[p]-1;', r'''
          response_count[qjob[p][qhead[p]]]=response_count[qjob[p][qhead[p]]]+1;
          if(response_count[qjob[p][qhead[p]]]==8*active_k/4) service_cycle[qjob[p][qhead[p]]]=cycles;
          qhead[p]=(qhead[p]+1)%4;qcount[p]=qcount[p]-1;
''')
    return source+SERVICE+DRIVER


def events(directory, seed):
    directory.mkdir(parents=True, exist_ok=True)
    ready, latency = directory/f'ready-{seed}.hex', directory/f'latency-{seed}.hex'
    if not ready.exists():
        rng = [random.Random(seed*1000033+lane) for lane in range(10)]
        with ready.open('w') as stream:
            for _ in range(1000000):
                stream.write(f'{sum((r.randrange(4)!=0)<<lane for lane,r in enumerate(rng)):03x}\n')
    if not latency.exists():
        with latency.open('w') as stream:
            for lane in range(10):
                for ordinal in range(17600):
                    stream.write(f'{random.Random(seed*1000003+lane*1009+ordinal).randint(1,7):x}\n')
    return ready, latency


def compare(reference, candidate):
    keys = ('K', 'mapping', 'seed', 'profile', 'output_stall')
    old = {tuple(c[k] for k in keys): c for c in reference['cases']}
    new = {tuple(c[k] for k in keys): c for c in candidate['cases']}
    errors = []
    if len(old) != 162 or len(new) != 162 or old.keys() != new.keys():
        errors.append('all 162 identical-workload cases are required')
    if reference['workload_digest'] != candidate['workload_digest'] or reference['checker_digest'] != candidate['checker_digest']:
        errors.append('workload/checker changed')
    for key in old.keys() & new.keys():
        for metric in ('completion_cycles', 'supply_cycles'):
            if new[key][metric] > old[key][metric]:
                errors.append(f'{key}: {metric} increased')
        if new[key]['useful_bytes'] != old[key]['useful_bytes']:
            errors.append(f'{key}: useful DRAM bytes changed')
    return dict(verdict='failed' if errors else 'passed', errors=errors)


def measure(root, rtl, output, *, event_directory, reference=None):
    output.mkdir(parents=True, exist_ok=False)
    checker = root/'verif/tb_lb.sv'; original = checker.read_bytes()
    tb = output/'tb_folding_perf.sv'; tb.write_text(testbench(original.decode()))
    sim = output/'simulation'
    command(root, [os.environ['IVERILOG_EXE'], '-g2012', '-s', 'tb_lb', '-o', sim, rtl, tb], output/'compile.log', 120)
    jobs, hashes = [], [digest(tb)]
    for seed in (11, 23, 37):
        ready, latency = events(event_directory, seed)
        hashes.extend([digest(ready), digest(latency)])
        rng = random.Random(seed)
        x = [rng.randrange(-128, 128) for _ in range(64)]
        w = [[rng.randrange(-128, 128) for _ in range(8)] for _ in range(64)]
        for k in (4, 16, 64):
            expected = [sum(x[i]*w[i][j] for i in range(k)) for j in range(8)]
            vector = output/f'vectors-{seed}-{k}.txt'
            vector.write_text(' '.join(map(str, [*x, *[v for row in w for v in row], *expected]))+'\n')
            hashes.append(digest(vector))
            for mapping, code in [('normal', 0), ('lane0_to8', 1), ('lane0_to8_lane7_to9', 32769)]:
                for profile, number in [('fast', 0), ('jitter', 1), ('burst', 2)]:
                    for stall in (0, 1):
                        log = output/f'K{k}-{mapping}-{seed}-{profile}-stall{stall}.log'
                        args = [os.environ['VVP_EXE'], sim, f'+perf_k={k}', f'+perf_map={code}',
                                f'+perf_profile={number}', f'+perf_stall={stall}', '+vectors='+str(vector),
                                '+ready_events='+str(ready), '+latency_events='+str(latency)]
                        jobs.append((dict(K=k,mapping=mapping,seed=seed,profile=profile,output_stall=stall),args,log))
    def run_case(job):
        case,args,log = job
        # Four independent one-core simulations share the frozen four-core budget.
        # Wall time accommodates buffer-model events; the cycle watchdog is unchanged.
        command(root,args,log,600)
        match = re.search(r'FOLD_PERF_PASS jobs=1100 intervals=1000 completion_cycles=(\d+) supply_cycles=(\d+) useful_bytes=(\d+) max_latency=(\d+)',log.read_text())
        if not match:raise ValueError('missing measured performance pass marker')
        values = list(map(int,match.groups()))
        if min(values[:2]) <= 0 or values[2] != 1000*8*case['K']:raise ValueError('invalid performance counters')
        return dict(**case,completion_cycles=values[0],supply_cycles=values[1],useful_bytes=values[2],
                    max_latency_cycles=values[3],log_digest=digest(log))
    with ThreadPoolExecutor(max_workers=4) as pool:
        cases = list(pool.map(run_case,jobs))
    if checker.read_bytes() != original:
        raise ValueError('immutable original checker changed')
    data = dict(schema_version=1, verdict='passed', cases=cases, rtl_digest=digest(rtl),
                checker_digest=digest(tb), workload_digest=hashlib.sha256(''.join(hashes).encode()).hexdigest(),
                execution=dict(simulation_workers=4,per_case_wall_seconds=600,functional_cycle_watchdog=1000000),
                scope='1000 steady completion/service intervals after 100 warmup jobs; identical fixed schedules')
    if reference is not None:
        data['comparison'] = compare(reference, data); data['verdict'] = data['comparison']['verdict']
    save(output/'performance.json', data)
    return data
