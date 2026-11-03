#!/usr/bin/env ruby
# KLayout batch script: render a GDS top cell to a PNG.
# Usage (inside devshell):
#   klayout -b -r render_gds.lym -rd input=<file.gds> -rd output=<file.png> -rd width=1600
input  = $input
output = $output
width  = $width ? $width.to_i : 1600

view = RBA::LayoutView.new
view.load_layout(input, 0)
view.max_hier
view.zoom_fit

# Compute height from aspect ratio so the image isn't stretched.
bb = view.active_cellview.cell.bbox
h = (width.to_f * bb.height / bb.width).round.clamp(200, 4000)

view.save_image(output, width, h)
puts "rendered #{output} (#{width}x#{h})"
