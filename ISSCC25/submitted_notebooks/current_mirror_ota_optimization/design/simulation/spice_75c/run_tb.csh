#!/bin/tcsh

# Check if PDK_ROOT and ROAR_DESIGN are set
if (! $?PDK_ROOT) then
    echo "Error: PDK_ROOT is not set. Please set PDK_ROOT to the SkyWater PDK installation path."
    exit 1
endif

if (! $?ROAR_DESIGN) then
    echo "Error: ROAR_DESIGN is not set. Please set ROAR_DESIGN to your design's base directory."
    exit 1
endif

# Input and output SPICE files
set input_file = "$ROAR_DESIGN/cm_ota/simulation/spice_75c/tb_cm_ota.sp"
set output_file = "$ROAR_DESIGN/cm_ota/simulation/spice_75c/tb_cm_ota_preprocessed.sp"
set log_file = "$ROAR_DESIGN/cm_ota/simulation/spice_75c/output.log"

# Check if the input file exists
if (! -e $input_file) then
    echo "Error: SPICE file $input_file not found."
    exit 1
endif

# Use awk to replace $PDK_ROOT and $ROAR_DESIGN
awk -v PDK_ROOT="$PDK_ROOT" -v ROAR_DESIGN="$ROAR_DESIGN" \
    '{gsub(/\$PDK_ROOT/, PDK_ROOT); gsub(/\$ROAR_DESIGN/, ROAR_DESIGN); print}' \
    $input_file > $output_file

# Verify that the preprocessing was successful
if (! -e $output_file) then
    echo "Error: Failed to create the preprocessed SPICE file."
    exit 1
endif

# Run ngspice with the preprocessed SPICE file and save output to the log file
ngspice -b -o $log_file $output_file
#ngspice -b $output_file
#ngspice $output_file


# Check if ngspice ran successfully
if ($status != 0) then
    echo "Error: ngspice simulation failed. Check the log file for details: $log_file"
    exit 1
endif

echo "ngspice simulation completed successfully. Output saved in $log_file."
