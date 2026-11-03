"""Independently measure reset requirements from the recorded environment VCD."""
def measure_reset(samples):
    previous = {}
    last_rise = None
    low_start = None
    releases = []
    for timestamp, values in samples:
        if values['clk'] == 1 and previous.get('clk') != 1: last_rise = timestamp
        if values['rst_n'] == 0:
            if previous.get('rst_n') != 0: low_start = timestamp
            assert all(values[n] == 0 for n in ['pending','data0','data1','host','imem_valid',
                'dmem_req_valid','dmem_rsp_ready','commit_valid','trap_valid']), 'Reset state/output'
            if last_rise is not None:
                assert values['imem_rdata'] == 0x13, 'Instruction memory reset after clock edge'
        elif previous.get('rst_n') == 0:
            low_ns = (timestamp-low_start)/1000
            phase_ns = (timestamp-last_rise)/1000
            assert low_ns >= 200 and 49 <= phase_ns-1 <= phase_ns+1 <= 51, 'Reset waveform budget'
            releases.append({'assert_ns':low_start/1000,'release_ns':timestamp/1000,
                'low_pulse_ns':low_ns,'release_after_rising_edge_ns':phase_ns,
                'bounded_skew_ns':1,'release_interval_with_skew_ns':[phase_ns-1,phase_ns+1],
                'joint_memory_reset':True})
        previous = values
    assert len(releases) == 1
    return releases

def vcd_samples(path):
    names = {}; values = {}; timestamp = 0; samples = []; header = True
    required = ['clk','rst_n','pending','data0','data1','host','imem_rdata','imem_valid',
        'dmem_req_valid','dmem_rsp_ready','commit_valid','trap_valid']
    text = path.read_text()
    assert '$timescale 1ps $end' in ' '.join(text.split()), 'Waveform timescale'
    for line in text.splitlines():
        fields = line.split()
        if header:
            if fields and fields[0] == '$var' and fields[4] in required: names[fields[3]] = fields[4]
            if '$enddefinitions' in line: header = False
            continue
        if line.startswith('#'):
            if set(values) == set(required): samples.append((timestamp,dict(values)))
            timestamp = int(line[1:])
        elif line and line[0] in '01' and line[1:] in names: values[names[line[1:]]] = int(line[0])
        elif line.startswith('b') and len(fields) == 2 and fields[1] in names:
            values[names[fields[1]]] = int(fields[0][1:],2)
    if set(values) == set(required): samples.append((timestamp,dict(values)))
    assert samples
    return samples

