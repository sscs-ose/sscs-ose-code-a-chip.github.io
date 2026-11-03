"""Pinned SAR digital XSPICE + transistor comparator/CDAC partition.

Digital logic is the upstream synthesized gate network with fixed XSPICE
delays, not an ideal quantizer. Analog uses upstream schematic devices.
External ideal VCM is explicit; this is not full-top transistor RC PEX.
"""
from pathlib import Path
import re

FILES=('adc_core_digital.v.xspice','adc_clkgen_with_edgedetect.v.xspice',
       'adc_array_matrix_12bit.sch.spice','adc_comp_latch.sch.spice')


def stable_log_cosh(text):
    """Exact algebraic rewrite avoiding overflow during Newton trial voltages.

    log(cosh(x)) = abs(x)+log(1+exp(-2*abs(x)))-log(2). No clamping,
    parameter fitting, device omission or installed PDK edits.
    """
    output=[];start=0;count=0
    while True:
        at=text.find('log(cosh(',start)
        if at<0:output.append(text[start:]);break
        begin=at+9;depth=1;end=begin
        while end<len(text) and depth:
            depth += (text[end]=='(')-(text[end]==')');end+=1
        if depth or end>=len(text) or text[end]!=')':raise ValueError('unbalanced log(cosh) model expression')
        expr=text[begin:end-1]
        output += [text[start:at],f'(abs({expr})+log(1+exp(-2*abs({expr})))-log(2))']
        start=end+1;count+=1
    return ''.join(output),count


def cards(text):
    out=[]
    for row in text.splitlines():
        if row.startswith('+'):
            if not out:raise ValueError('orphan continuation')
            out[-1]+=' '+row[1:].strip()
        else:out.append(row)
    return out


def ports(text,cell):
    rows=[r.split()[2:] for r in cards(text) if re.match(r'(?i)^\.subckt\s+'+re.escape(cell)+r'\s',r)]
    if len(rows)!=1:raise ValueError('one subcircuit required: '+cell)
    return rows[0]


def name(port):
    return re.sub(r'\[(\d+)\]',r'_\1',port.removeprefix('a_')).rstrip('_').lower()


def power(n):
    return {'vpwr':'VPWR','vdd':'VPWR','vgnd':'0','vss':'0'}.get(n)


def core_node(port):
    n=name(port)
    return power(n) or {'clk_dig_in':'ADC_CLK_DIG','comparator_in':'LATCH_Q',
        'conv_finished_out':'EOC','conv_finished_osr_out':'EOC_OSR',
        'enable_loop_out':'ENA','rst_n':'RST_N'}.get(n,n)


def clock_node(port):
    n=name(port)
    exact={'clk_comp_out':'ADC_CLK_COMP','clk_dig_out':'ADC_CLK_DIG','ena_in':'ENA',
        'enable_dlycontrol_in':'config_2_in_15','ndecision_finish_in':'COMP_TRIG','start_conv_in':'START',
        'sample_p_in':'sample_matrix_out','sample_n_in':'sample_matrix_out',
        'nsample_p_in':'sample_matrix_out_n','nsample_n_in':'sample_matrix_out_n',
        'sample_p_out':'SAMPLE_P','sample_n_out':'SAMPLE_N',
        'nsample_p_out':'SAMPLE_P_N','nsample_n_out':'SAMPLE_N_N'}
    m=re.fullmatch(r'dlycontrol([1-4])_in_(\d+)',n)
    if m:
        group,bit=map(int,m.groups())
        return 'config_1_in_'+str(10+bit) if group==4 else 'config_2_in_'+str((group-1)*5+bit)
    if power(n):return power(n)
    if n not in exact:raise ValueError('unknown clock port: '+port)
    return exact[n]


def matrix_node(port,side):
    n=name(port)
    if power(n):return power(n)
    exact={'vcm':'VCM','sample':'SAMPLE_'+side,'sample_n':'SAMPLE_'+side+'_N',
        'en_c0_n':side.lower()+'matrix_c0_out_n','sw':'sample_switch_out',
        'sw_n':'sample_switch_out_n','analog_in':'AIN'+side,'ctop':'CTOP'+side}
    if n in exact:return exact[n]
    m=re.fullmatch(r'(row_n|rowon_n|rowoff_n|col_n|col|en_bit_n)_(\d+)',n)
    if not m:raise ValueError('unknown CDAC port: '+port)
    kind,bit=m.groups()
    stem={'row_n':'row_out_n','rowon_n':'rowon_out_n','rowoff_n':'rowoff_out_n',
          'col_n':'col_out_n','col':'col_out','en_bit_n':'bincap_out_n'}[kind]
    return side.lower()+'matrix_'+stem+'_'+bit


def subcircuits(text):
    result={};block=[];key=None
    for row in cards(text):
        if row.lower().startswith('.subckt '):key=row.split()[1];block=[row]
        elif key is not None:
            block.append(row)
            if row.lower().startswith('.ends'):
                result[key]='\n'.join(block);key=None
    if key is not None:raise ValueError('unterminated subcircuit')
    return result


def fast_matrix(text):
    """Retain all source capacitor values and real input TG; idealize bottom drivers.

    Boolean bottom-plate drive follows the schematic CMOS logic. No input
    quantization/code/EOC source exists. Per-cell switch resistance, parasitic
    charge injection and decoder hazards are outside this partition.
    """
    blocks=subcircuits(text);cell='adc_array_matrix_12bit'
    normalize=lambda s:re.sub(r'\[(\d+)\]',r'_\1',s)
    lines=['* CDAC approximation: exact schematic C inventory, ideal bottom drivers.',
           normalize(cards(blocks[cell])[0])]
    inventory=[];terms=[]
    for row in cards(blocks[cell])[1:]:
        f=row.split()
        if not f or not f[0].lower().startswith('x'):continue
        model=f[-1]
        if model not in blocks:raise ValueError('unresolved CDAC cell')
        caps=[r.split() for r in cards(blocks[model]) if r.lower().startswith('c')]
        if not caps:continue
        if len(caps)!=1:raise ValueError('one source capacitor per selected cell required')
        mapping=dict(zip(ports(blocks[model],model),map(normalize,f[1:-1])))
        index=len(inventory);value=caps[0][3];inventory.append(value)
        if model.endswith('_8'):
            high=f'(v({mapping["rowon_n"]})<.9 || (v({mapping["row_n"]})<.9 && v({mapping["col_n"]})<.9))'
        else:high=f'(v({mapping["en_n"]})<.9)'
        cap=float(value[:-1])*1e-15 if value.lower().endswith('f') else float(value)
        terms.append((cap,f'({high} ? v(VDD) : v(VSS))'))
    if len(inventory)!=515:raise ValueError('pinned CDAC must retain all 515 schematic signal capacitors')
    # Exact linear-capacitor identity: sum Ci*d(Vtop-Vbi)/dt equals
    # Ctotal*d(Vtop-sum(Ci*Vbi)/Ctotal)/dt. No ADC decision is computed here.
    total=sum(c for c,_ in terms)
    weighted=' + '.join(f'{c/total:.17g}*{expr}' for c,expr in terms)
    lines += [f'BBOTTOM bottom VSS v=(v(sample)>.9 ? v(vcm) : ({weighted}))',
              f'CSUM ctop bottom {total:.17g}',
              'XSAMPLE sw_n analog_in sw ctop VDD VSS adc_gate_switch','.ends '+cell,
              blocks['adc_gate_switch']]
    return '\n'.join(lines)+'\n',inventory


def library(source,*,fast_cdac=True):
    texts={f:(Path(source)/f).read_text() for f in FILES}
    if fast_cdac:texts[FILES[2]],_=fast_matrix(texts[FILES[2]])
    # .end terminates a deck; keep .ends and every device/model unchanged.
    body='\n'.join(re.sub(r'(?im)^\.end\s*$','',texts[f]) for f in FILES)
    core=ports(texts[FILES[0]],'adc_core_digital')
    clock=ports(texts[FILES[1]],'adc_clkgen_with_edgedetect')
    matrix=ports(texts[FILES[2]],'adc_array_matrix_12bit')
    lines=[body,'* Actual SAR feedback; external ideal common-mode reference.',
        'XCORE '+' '.join(map(core_node,core))+' adc_core_digital',
        'XCGEN '+' '.join(map(clock_node,clock))+' adc_clkgen_with_edgedetect',
        'XPMAT '+' '.join(matrix_node(p,'P') for p in matrix)+' adc_array_matrix_12bit',
        'XNMAT '+' '.join(matrix_node(p,'N') for p in matrix)+' adc_array_matrix_12bit',
        'XCOMP VPWR 0 ADC_CLK_COMP CTOPP CTOPN COMP_TRIG LATCH_QN LATCH_Q adc_comp_latch']
    # The terminal names are taken from the upstream formal interfaces.
    return '\n'.join(lines)+'\n'


def bench(model,source,*,diff=.1,cm=.9,stop_s=2e-6,start_s=200e-9,fast_cdac=True):
    if not 0<=cm-abs(diff)/2<=cm+abs(diff)/2<=1.8:raise ValueError('input outside supply')
    text=['SAR ADC partition: pinned digital gates + transistor CDAC/comparator',
        f'.lib "{model}" tt','.param mc_mm_switch=0','.temp 25',
        '.option klu method=gear reltol=1e-3 abstol=1e-12',
        library(source,fast_cdac=fast_cdac),'VVDD VPWR 0 1.8','VVCM VCM 0 .9',
        'VRST RST_N 0 PWL(0 0 100n 0 100.1n 1.8)',
        f'VSTART START 0 PWL(0 0 {start_s:.12g} 0 {start_s+1e-10:.12g} 1.8 {start_s+20e-9:.12g} 1.8 {start_s+20.1e-9:.12g} 0)',
        f'VINP AINP 0 {cm+diff/2:.12g}',f'VINN AINN 0 {cm-diff/2:.12g}']
    for reg,val in ((1,0x0400),(2,0x8421)):
        text += [f'VCFG{reg}_{b} config_{reg}_in_{b} 0 '+('1.8' if val&(1<<b) else '0') for b in range(16)]
    vectors=['v('+n+')' for n in ('AINP','AINN','RST_N','START','EOC','EOC_OSR','ADC_CLK_DIG',
        'ADC_CLK_COMP','CTOPP','CTOPN','COMP_TRIG','LATCH_Q',*(f'result_out_{b}' for b in range(16)))]
    text += [f'.tran .5n {stop_s:.12g} 0 .5n','.save '+' '.join(vectors),
        '.control','set filetype=ascii','set numdgt=17','run',
        'write adc.raw '+' '.join(vectors),'echo AUTOMX_ADC_PARTITION_DONE','quit','.endc','.end','']
    return '\n'.join(text)
