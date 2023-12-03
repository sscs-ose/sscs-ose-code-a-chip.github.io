
# Assign input .gds file to a variable
input_gds_file="$1"

# Extract the file name from input .gds
file_name=$(basename -- "$input_gds_file")
file_name_no_ext="${file_name%.*}"

# Open magic and convert to gds
conda-env/bin/magic -dnull -noconsole -T conda-env/share/pdk/sky130A/libs.tech/magic/sky130A.tech -rcfile conda-env/share/pdk/sky130A/libs.tech/magic/sky130A.magicrc <<EOF
gds read $input_gds_file
lef write $file_name_no_ext.lef
quit -noprompt
EOF
