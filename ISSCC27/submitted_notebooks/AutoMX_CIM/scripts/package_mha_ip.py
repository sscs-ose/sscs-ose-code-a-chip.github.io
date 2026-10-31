"""Export source IP, functional tests and the bound hard-macro views."""
from pathlib import Path
import io,json,tarfile


def package(root,analog_views=None):
    root=Path(root).resolve();folder=root/'exports';folder.mkdir(exist_ok=True)
    target=folder/'AutoMX_MHA_IP_20261028.tar.gz';prefix='AutoMX_MHA_IP'
    sources=[p for p in (root/'ip/automx_mha').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    sources += [root/'rtl/automx_cim_readout_seq.sv']
    names=['automx_cim_mixed_signal_proto.sv','wrapper_blackboxes.sv','experiment_spec.json',
           'core.lef','core.gds','conditioner.lef','conditioner.gds','adc.lef','adc.gds',
           'macro_placement.cfg','pdn_mixed_wrapper.tcl','repair_wrapper_ground.tcl','openlane_config_template.json']
    sources += [root/'inputs'/name for name in names]
    sources += [p for p in (root/'inputs/digital_blocks').rglob('*') if p.is_file()]
    sources += [root/'scripts/harden_digital_blocks.py',root/'scripts/harden_pulse_readout.py',root/'scripts/build_physical_range_core.py',root/'scripts/reduce_pex_resistors.py',root/'scripts/group_parallel_mim.py',root/'standalone.json']
    sources += [root/'scripts/verify_binary_decoder.py', root/'scripts/verify_ternary_backend.py']
    sources += [p for p in [root/'LICENSE',root/'NOTICE.md',root/'third_party/SKY130_SAR_ADC1/LICENSE'] if p.is_file()]
    readme='''# AutoMX MHA RTL IP\n\nCopyright 2026 EDABK Laboratory.\n\nThis package contains the synthesizable 2-token, 4-channel, 2-head MHA IP, its CIM/SAR integrated RTL top, both functional testbenches, and five hard-macro LEF/GDS views, including independently routed MHA and readout/calibration. No stored simulation results are used as test inputs.\n\nRun from this extracted folder using Python with NumPy and native Icarus Verilog installed:\n\n```bash\npython ip/automx_mha/verify.py --root . --work output\n```\n\nSee ip/automx_mha/README.md and manifest.json for ports, number formats, softmax approximation and verification scope. Use the included FuseSoC filesets or your ASIC flow to bind the physical macro views from inputs/. The digital blocks also carry routed gate netlists and SPEFs for hierarchical STA. Their Liberty models contain physical port constraints for placement/CTS; actual timing uses the gate netlists and extracted parasitics. SKY130 PDK and physical tools are external flow dependencies. The full laboratory notebook supplies their configuration and cold implementation.\n'''
    with tarfile.open(target,'w:gz') as archive:
        data=readme.encode();info=tarfile.TarInfo(prefix+'/README.md');info.size=len(data);info.mode=0o644
        archive.addfile(info,io.BytesIO(data))
        for p in sorted(set(sources)):
            if analog_views and p.parent==root/'inputs' and p.name in ('core.gds','core.lef'):continue
            archive.add(p,arcname=str(Path(prefix)/p.relative_to(root)),recursive=False)
        if analog_views:
            analog_views=Path(analog_views).resolve()
            for name in ('core.gds','core.lef','core_acquisition.spice','core_acquisition.pex.spice','core_acquisition.compact.spice'):
                if (analog_views/name).is_file():archive.add((analog_views/name).resolve(),arcname=str(Path(prefix)/'inputs'/name),recursive=False)
    with tarfile.open(target) as archive: file_count=len(archive.getmembers())
    report={'archive':str(target),'files':file_count,'size_bytes':target.stat().st_size,
            'stored_measurement_results_included':False,'source_and_hard_macro_views':True,'selected_analog_views':str(analog_views) if analog_views else None}
    (folder/'AutoMX_MHA_IP_20261028.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return target

if __name__=='__main__':package(Path(__file__).resolve().parents[1])
