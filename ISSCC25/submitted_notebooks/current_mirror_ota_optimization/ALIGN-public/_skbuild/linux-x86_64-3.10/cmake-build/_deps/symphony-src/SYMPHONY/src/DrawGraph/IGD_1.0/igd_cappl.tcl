#!/usr/local/ccop/local/bin/wish

source Init.tcl
source Tools.tcl
source NodeEdgeBasics.tcl
source FileMenu.tcl
source WindowMenu.tcl
source NodeMenu.tcl
source EdgeMenu.tcl
source CAppl.tcl

Igd_StartUp

Igd_SetApplDefaults 1000 800 550 400 1 1 1 "" "3 3" 8 1 1 1 -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-* -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-* -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-*

Igd_CopyApplDefaultToWindow 1
Igd_InitWindow 1 "first window"
Igd_DisplayWindow 1
Igd_EnableCAppl 1

Igd_LoadGraph 1 "dantzig.g"

Igd_CApplSetCmsg 1 "The nodes of the graphs represent \n42 major cities of the United States.\nThe edges present show the shortest \nHamiltonian circuit on these nodes.\n"