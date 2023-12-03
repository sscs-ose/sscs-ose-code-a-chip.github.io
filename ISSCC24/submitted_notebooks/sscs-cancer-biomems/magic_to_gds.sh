
# Assign input .mag file to a variable
input_mag_file="$1"

# Extract the file name from input .mag
file_name=$(basename -- "$input_mag_file")
file_name_no_ext="${file_name%.*}"

# Open magic and convert to gds
conda-env/bin/magic -dnull -noconsole -T conda-env/share/pdk/sky130A/libs.tech/magic/sky130A.tech -rcfile conda-env/share/pdk/sky130A/libs.tech/magic/sky130A.magicrc <<EOF
load avsd_opamp/layout_design/avsd_opamp_layout.mag
gds write $file_name_no_ext.gds
lef write $file_name_no_ext.lef
quit -noprompt
EOF
