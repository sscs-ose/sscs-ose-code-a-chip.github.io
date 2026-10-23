from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
threads = int(sys.argv[3])
text = source.read_text(encoding="utf-8")

if text.count("threads(4)") != 1:
    raise SystemExit("expected one threads(4)")
text = text.replace("threads(4)", f"threads({threads})", 1)

anchor = "netlist # ... not really required"
if text.count(anchor) != 1:
    raise SystemExit("expected one netlist anchor")
checkpoint = r'''puts "A3_RUN8_PHASE=NETLIST_EXTRACTION_START|utc=#{Time.now.utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
netlist # ... not really required
puts "A3_RUN8_PHASE=NETLIST_EXTRACTION_DONE|utc=#{Time.now.utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
writer = RBA::NetlistSpiceWriter::new
writer.use_net_names = true
netlist.write($extracted_cdl, writer, "A3 run8 extracted netlist checkpoint")
lvs_data.write_l2n($l2n_file)
raise "A3_RUN8_EXTRACTED_CDL_EMPTY" unless File.size?($extracted_cdl)
raise "A3_RUN8_L2N_EMPTY" unless File.size?($l2n_file)
puts "A3_RUN8_PHASE=CHECKPOINT_WRITTEN|cdl=#{$extracted_cdl}|l2n=#{$l2n_file}|utc=#{Time.now.utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
exit(0)'''
text = text.replace(anchor, checkpoint, 1)
target.write_text(text, encoding="utf-8")
