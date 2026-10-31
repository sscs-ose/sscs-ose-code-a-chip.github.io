"""Setup, measured plots and final manifest for the executable prototype notebook."""
import json
from pathlib import Path
import shutil
import sys
import tarfile
import numpy as np
from scripts.flow2_runall_support import digest,item,save,verified

ARCHIVE_SHA='e7dadfb7bd5474fd22409c1e5a67acdec19f77e597df68e17c5549bc1390d7fd'


def prepare_shared(flow):
    """Use an installed tool binary or build it; probe it with a new native process."""
    folder=flow.base/'tools/ngspice_shared44';lib=folder/'install/lib/libngspice.so'
    provenance=folder/'provenance.json'
    import os
    installed=Path(os.environ.get('AUTOMX_NGSPICE_LIBRARY','/media/nam/EDABK/AutoMX_CIM_tools/ngspice_shared44/libngspice.so'))
    if not lib.is_file() and installed.is_file():
        lib.parent.mkdir(parents=True,exist_ok=True);lib.symlink_to(installed.resolve())
        save(provenance,dict(version='44.2',archive_sha256=ARCHIVE_SHA,kind='installed_tool_binary',library=item(installed)))
    if not lib.is_file():
        archive=flow.root/'build/tools/ngspice-44.2/ngspice-44.2.tar.gz'
        if not archive.is_file():raise FileNotFoundError('Provide official ngspice-44.2.tar.gz at '+str(archive))
        if digest(archive)!=ARCHIVE_SHA:raise ValueError('ngspice source archive SHA mismatch')
        folder.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not (folder/member.name).resolve().is_relative_to(folder.resolve()):raise ValueError('unsafe archive path')
            tar.extractall(folder,filter='data')
        source=folder/'ngspice-44.2';build=folder/'build';build.mkdir(exist_ok=True)
        configure=[source/'configure','--prefix='+str(folder/'install'),'--with-ngshared','--with-x=no',
            '--with-readline=no','--enable-xspice','--enable-klu','--disable-debug']
        flow.run('ngspice_configure',configure,inputs=[archive],outputs=[build/'Makefile'],cwd=build,timeout_s=120)
        flow.run('ngspice_make',['make','-j'+str(min(flow.settings.jobs*2,8))],inputs=[archive,build/'Makefile'],
            outputs=[build/'src/.libs/libngspice.so'],cwd=build,timeout_s=600)
        flow.run('ngspice_install',['make','install'],inputs=[build/'src/.libs/libngspice.so'],outputs=[lib],cwd=build,timeout_s=120)
        save(provenance,dict(version='44.2',archive_sha256=ARCHIVE_SHA,commands=[list(map(str,configure)),['make'],['make','install']],purpose='isolated shared-library mixed-signal co-simulation'))
    if not provenance.is_file() or json.loads(provenance.read_text()).get('archive_sha256')!=ARCHIVE_SHA:
        raise ValueError('shared ngspice build provenance absent or changed')
    record=flow.work/'ngspice_runtime.json'
    save(record,dict(library=item(lib),build_provenance=item(provenance),version='44.2'))
    flow.outputs['ngspice_runtime']=item(record)
    print('Pinned shared ngspice:',json.dumps(json.loads(record.read_text()),indent=2))
    probe=flow.work/'ngspice_version.py'
    probe.write_text("import ctypes,sys\n"
        "lib=ctypes.CDLL(sys.argv[1])\n"
        "callback=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_void_p)\n"
        "def output(message,*_):\n print(message.decode(errors='replace'),flush=True);return 0\n"
        "emit=callback(output)\nlib.ngSpice_Init(emit,None,None,None,None,None,None)\n"
        "raise SystemExit(lib.ngSpice_Command(b'version'))\n")
    native=flow.run('ngspice_runtime_version',[sys.executable,probe,lib],inputs=[probe,lib],timeout_s=30)
    text=Path(native['log']['path']).read_text()
    if 'ngspice-44' not in text:raise ValueError('expected ngspice 44 runtime')
    return lib


def environment(flow):
    print('env_mamba interpreter:',sys.executable)
    print('Free persistent work disk, GiB:',round(shutil.disk_usage(flow.base).free/1024**3,1))
    script=flow.work/'versions.py'
    script.write_text('import subprocess,sys\nprint("Python:",sys.executable,sys.version)\n'
        'for c in (["iverilog","-V"],["vvp","-V"],["klayout","-b","-v"],["docker","--version"]):\n'
        ' r=subprocess.run(c,text=True,capture_output=True,timeout=15);print("$"," ".join(c));print(r.stdout+r.stderr);r.check_returncode()\n')
    flow.run('host_versions',[sys.executable,script],inputs=[script],timeout_s=90)
    for tool,arg in [('yosys','-V'),('openroad','-version')]:
        flow.run(tool+'_version',flow.container(tool,[arg],tool+'_version'),timeout_s=30)


def plot_conversion(flow,case_receipt):
    import matplotlib.pyplot as plt
    from scripts.flow2_waveforms import read_raw
    path=verified(case_receipt);summary=json.loads(path.read_text());raw=path.parent/'coupled.raw'
    # The native step receipt binds this raw waveform to the measured case.
    job=json.loads((path.parent/'step.json').read_text())
    record=next(v for v in job['outputs'] if Path(v['path'])==raw)
    waves=read_raw(verified(record));t=waves['time']*1e9
    fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True,layout='constrained')
    axes[0].plot(t,(waves['v(ainp)']-waves['v(ainn)'])*1000,label='CIM + conditioner → ADC input')
    axes[0].plot(t,(waves['v(ctopp)']-waves['v(ctopn)'])*1000,label='CDAC top differential');axes[0].set_ylabel('mV');axes[0].legend()
    for node in ('adc_clk_comp','latch_q','sample'):axes[1].plot(t,waves['v('+node+')'],label=node)
    axes[1].set_ylabel('V');axes[1].legend(ncol=3)
    for node in ('start','eoc'):axes[2].plot(t,waves['v('+node+')'],label=node)
    axes[2].set_ylabel('V');axes[2].legend()
    word=sum((waves[f'v(result_{bit})']>.9).astype(int)*(1<<bit) for bit in range(16))
    axes[3].step(t,word>>4,where='post',label='ADC word[15:4] (electrical RTL bridge)')
    axes[3].set_ylabel('12-bit code');axes[3].set_xlabel('Native ngspice time / ns');axes[3].legend()
    for ax in axes:ax.grid(alpha=.2);ax.axvline(summary['eoc_s']*1e9,color='gray',ls=':')
    fig.suptitle(f'Real transistor/RTL partition: code {summary["result_code_12bit"]}, {summary["cycles"]} SAR cycles')
    path=flow.work/'adc_native_waveform.png';fig.savefig(path,dpi=140);plt.show();plt.close(fig)
    flow.outputs['adc_waveform_png']=item(path)
    return summary


def plot_mha(flow,report):
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,3.5),layout='constrained')
    for ax,key,title in zip(axes,('reference_quantized_output','output'),('Quantized reference','Measured CIM/ADC → MHA')):
        image=ax.imshow(report[key],cmap='coolwarm',vmin=-2,vmax=2);ax.set_title(title);ax.set_xlabel('Output dimension');ax.set_ylabel('Token')
    rows=report['jobs'];axes[2].scatter([r['reference_integer_sum'] for r in rows],[r['unrounded_calibrated_sum'] for r in rows],s=20)
    lo=min(r['reference_integer_sum'] for r in rows);hi=max(r['reference_integer_sum'] for r in rows)
    axes[2].plot([lo,hi],[lo,hi],'k--');axes[2].set_xlabel('Reference integer sum');axes[2].set_ylabel('Frozen-calibration ADC decode');axes[2].set_title('32 measured projection transactions')
    fig.colorbar(image,ax=axes[:2],shrink=.8)
    path=flow.work/'mha_measured.png';fig.savefig(path,dpi=140);plt.show();plt.close(fig);flow.outputs['mha_png']=item(path)


def publish(flow):
    required=('analog_adc_mha','mapped_synthesis','mapped_sar','gds','lef','def','gds_geometry_proof','gds_drc_summary','signal_lvs','power','spef','lib','sdc','top_png')
    for key in required:verified(flow.outputs[key])
    mha=json.loads(verified(flow.outputs['analog_adc_mha']).read_text())
    if mha['status']!='MEASURED_PARTITION_ANALOG_ADC_MHA_END_TO_END_PASS':raise ValueError('measured MHA gate did not pass')
    for r in flow.receipts.values():
        for value in json.loads(verified(r).read_text()).get('outputs',[]):verified(value)
    drc=json.loads(verified(flow.outputs['gds_drc_summary']).read_text())
    report=dict(status='RUNALL_MIXED_SIGNAL_PARTITION_PROTOTYPE_WITH_PHYSICAL_WAIVERS',tag=flow.settings.tag,
        views=flow.outputs,native_steps=flow.receipts,drc=drc,fabrication_ready=False,qualification='NOT_QUALIFIED',
        placement_routing='Hash-verified routed checkpoint reused; fresh Yosys synthesis is a separate result, not routed again.',
        functional_scope=mha['scope'],physical_scope='Fresh DEF/LEF/GDS streamout; exact geometry equality to GDS-LVS source; native KLayout BEOL/off-grid DRC with explicit results/waivers (FEOL disabled), normalized signal Netgen LVS, PG connectivity, nominal digital RC/STA/ETM. '
        'Existing antenna, powered transistor LVS, Magic DRC, slew/fanout/coverage, analog PVT/noise/PEX, padframe and IR/EM gaps remain open.',
        end_to_end_partition_demonstrated=True,whole_chip_transistor_verified=False,physical_verification_complete=False,
        functional_shape=mha['shape'],projection_transactions=mha['projection_transactions'],unique_holdout_patterns=mha['unique_holdout_patterns'],
        relative_l2_quantized_reference=mha['relative_l2'],nominal_timing=flow.outputs['nominal_timing'])
    folder=flow.root/'physical/sky130/wrapper_prototype/integration'/flow.settings.tag
    folder.mkdir(parents=True,exist_ok=True)
    for key in ('gds','lef','def','lib','spef','sdc'):
        target=verified(flow.outputs[key]);link=folder/target.name
        if link.is_symlink() and link.resolve()==target:continue
        if link.exists() or link.is_symlink():raise FileExistsError('publish path already occupied: '+str(link))
        link.symlink_to(target)
    report['published_folder']=str(folder)
    path=flow.work/'runall_manifest.json';save(path,report)
    save(folder/'manifest.json',dict(manifest=item(path),views={k:flow.outputs[k] for k in ('gds','lef','def','lib','spef','sdc')}))
    # Small portable pointer receipt; large files stay on the persistent volume.
    save(flow.root/'results/receipts'/('flow2_runall_'+flow.settings.tag+'.json'),dict(manifest=item(path),status=report['status'],fabrication_ready=False))
    print(json.dumps({k:v for k,v in report.items() if k not in ('views','native_steps')},indent=2,ensure_ascii=False))
    print('Top GDS:',flow.outputs['gds']['path']);print('Complete manifest:',path)
    return report
