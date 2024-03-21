#!/bin/sh
export OPENRAM_TECH="/tmp/OpenRAM/technology:/tmp/OpenRAM/compiler/../technology"
echo "$(date): Starting LVS using Netgen /tmp/OpenRAM/miniconda/bin/netgen"
/tmp/OpenRAM/miniconda/bin/netgen -noconsole << EOF
lvs {myconfig.spice myconfig} {myconfig.lvs.sp myconfig} setup.tcl myconfig.lvs.report -full -json
quit
EOF
magic_retcode=$?
echo "$(date): Finished ($magic_retcode) LVS using Netgen /tmp/OpenRAM/miniconda/bin/netgen"
exit $magic_retcode
