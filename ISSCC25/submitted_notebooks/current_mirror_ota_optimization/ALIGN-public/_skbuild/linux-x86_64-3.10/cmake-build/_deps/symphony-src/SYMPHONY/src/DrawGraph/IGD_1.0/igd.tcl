#!/usr/local/bin/wish

source Init.tcl
source Tools.tcl
source NodeEdgeBasics.tcl
source FileMenu.tcl
source WindowMenu.tcl
source NodeMenu.tcl
source EdgeMenu.tcl

Igd_StartUp

Igd_SetApplDefaults 1000 800 550 400 0 1 1 "" "3 3" 4 1 1 1 -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-* -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-* -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-*

Igd_CopyApplDefaultToWindow 1
Igd_InitWindow 1 "first window"
Igd_DisplayWindow 1

Igd_LoadGraph 1 dantzig.g
