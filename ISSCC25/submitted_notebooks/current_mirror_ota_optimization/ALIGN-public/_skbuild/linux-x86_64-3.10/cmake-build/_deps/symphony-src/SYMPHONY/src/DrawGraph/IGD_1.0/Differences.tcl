###############################################################################
# This files contains those functions that are different for the cases when
# is run from an outside application (CAppl enabled) and when it is run just
# by itself.
###############################################################################


###############################################################################
# When igd is run from an outside application...
###############################################################################

proc Igd_set_filemenu { toplevel_name } {

    global igd_windowFromToplevel igd_windowDesc

    set window $igd_windowFromToplevel($toplevel_name)
    set m [menu $toplevel_name.mbar.file.menu -tearoff 0]
    
    $m add command -label "Load from file" \
	    -command "Igd_load_from_file $toplevel_name"
    $m add command -label "Save to file" \
	    -command "Igd_save_to_file $toplevel_name"
    $m add command -label "Save PostScript" \
	    -command "Igd_save_postscript_to_file $toplevel_name"
    $m add separator 
    $m add command -label "Quit from application" \
	    -command "Igd_CApplQuitAll"
}


proc Igd_QuitWindow { window } {

    global igd_windowToplevel igd_windowFromToplevel igd_windowTitle \
	    igd_windowNodes igd_windowNodeNum igd_windowNodeCount \
	    igd_windowEdges igd_windowEdgeNum igd_windowDesc \
	    igd_windowRegisters igd_applDescList igd_applWindows \
	    igd_applWindowCount igd_windowCApplEnabled

    set toplevel_name $igd_windowToplevel($window)

    # first erase the window
    Igd_EraseWindow $window

    # delete the mouse tracker if exists
    if { $igd_windowDesc(mouse_tracking,$window) } {
	Igd_DisableMouseTracking $window
    }

    # unset things that belong to the C application
    if { $igd_windowCApplEnabled($window) } {
	Igd_DisableCAppl $window
    }

    # destroy the window itself
    destroy $toplevel_name

    # unset variables corrsponding to window
    unset igd_windowToplevel($window) igd_windowFromToplevel($toplevel_name) \
	    igd_windowTitle($window) igd_windowNodes($window) \
	    igd_windowNodeNum($window) igd_windowNodeCount($window) \
	    igd_windowEdges($window) igd_windowEdgeNum($window) 

    foreach option $igd_applDescList {
	unset igd_windowDesc($option,$window)
    }

    foreach option {x y label node} {
	unset igd_windowRegisters(1,$option,$window)
	unset igd_windowRegisters(2,$option,$window)
    }

    # remove this window from the list of windows
    set pos [lsearch $igd_applWindows $window]
    set igd_applWindows [lreplace $igd_applWindows $pos $pos]
    incr igd_applWindowCount -1

    # if no window is left, invoke Igd_QuitAll
    if { $igd_applWindowCount == 0 } { Igd_QuitAll }
}









###############################################################################
# When igd is run by itself...
###############################################################################


proc Igd_set_filemenu { toplevel_name } {

    global igd_windowFromToplevel igd_windowDesc

    set window $igd_windowFromToplevel($toplevel_name)
    set m [menu $toplevel_name.mbar.file.menu -tearoff 0]
    
    $m add command -label "Load from file" \
	    -command "Igd_load_from_file $toplevel_name"
    $m add command -label "Save to file" \
	    -command "Igd_save_to_file $toplevel_name"
    $m add command -label "Save PostScript" \
	    -command "Igd_save_postscript_to_file $toplevel_name"
    $m add separator 
    $m add command -label "Quit from application" \
	    -command "Igd_QuitAll"
}


proc Igd_QuitWindow { window } {

    global igd_windowToplevel igd_windowFromToplevel igd_windowTitle \
	    igd_windowNodes igd_windowNodeNum igd_windowNodeCount \
	    igd_windowEdges igd_windowEdgeNum igd_windowDesc \
	    igd_windowRegisters igd_applDescList igd_applWindows \
	    igd_applWindowCount

    set toplevel_name $igd_windowToplevel($window)

    # first erase the window
    Igd_EraseWindow $window

    # delete the mouse tracker if exists
    if { $igd_windowDesc(mouse_tracking,$window) } {
	Igd_DisableMouseTracking $window
    }

    # destroy the window itself
    destroy $toplevel_name

    # unset variables corrsponding to window
    unset igd_windowToplevel($window) igd_windowFromToplevel($toplevel_name) \
	    igd_windowTitle($window) igd_windowNodes($window) \
	    igd_windowNodeNum($window) igd_windowNodeCount($window) \
	    igd_windowEdges($window) igd_windowEdgeNum($window) 

    foreach option $igd_applDescList {
	unset igd_windowDesc($option,$window)
    }

    foreach option {x y label node} {
	unset igd_windowRegisters(1,$option,$window)
	unset igd_windowRegisters(2,$option,$window)
    }

    # remove this window from the list of windows
    set pos [lsearch $igd_applWindows $window]
    set igd_applWindows [lreplace $igd_applWindows $pos $pos]
    incr igd_applWindowCount -1

    # if no window is left, invoke Igd_QuitAll
    if { $igd_applWindowCount == 0 } { Igd_QuitAll }
}
