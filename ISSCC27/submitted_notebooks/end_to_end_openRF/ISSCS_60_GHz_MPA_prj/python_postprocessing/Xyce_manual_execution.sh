PLUGIN="/home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/xyce/plugins/Xyce_Plugin_r3_cmc.so"
NETLIST="/home/matthi/QucsWorkspace/60_GHz_MPA_prj/60GHz_MPA_xyce_PDK_components_Base-T.cir"
LOG="/home/matthi/QucsWorkspace/60_GHz_MPA_prj/60GHz_MPA_xyce_PDK_components_Base-T.log"

Xyce -plugin "$PLUGIN" "$NETLIST" > "$LOG" 2>&1

echo "Xyce finished with exit code $?"
echo "Log written to: $LOG"