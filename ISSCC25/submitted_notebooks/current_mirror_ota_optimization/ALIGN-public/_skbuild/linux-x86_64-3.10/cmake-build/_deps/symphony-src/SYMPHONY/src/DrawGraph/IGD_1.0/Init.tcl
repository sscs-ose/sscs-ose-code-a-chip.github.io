#############################################################################
# This is the initialization process that needs to be invoked right after wish 
# is started. It sets variables and default values, and withdraws 
# the wish window so that only the application windows appear. 
#############################################################################

proc Igd_StartUp {} {

    global igd_applWindows igd_applWindowCount igd_applWindowNum \
	    igd_applDefaults \
	    igd_applIntPattern igd_applIntOrEmptyPattern igd_applDashPattern \
	    igd_applSpacesPattern igd_applDescList igd_applCheckFonts

    # initialize the list of application windows
    set igd_applWindows {}
    set igd_applWindowCount 0
    set igd_applWindowNum 0

    # set some patterns that will be used for checking inputs from the user
    set igd_applIntPattern {^[0-9]+$}
    set igd_applIntOrEmptyPattern {^ *$|^[0-9]+$}
    set igd_applDashPattern {^ *$|^( *[0-9]+ *)*$}
    set igd_applSpacesPattern {^ *$}

    # set this to 0 if you don't want the fonts to be checked whether they are 
    # valid or not. Be advised that the code will crash if you set this to 0
    # but give a fontname not recognized by xlsfonts.
    set igd_applCheckFonts 1
    
    # set the defaults for the entire application

    set igd_applDefaults(canvas_width)      600
    set igd_applDefaults(canvas_height)     400
    set igd_applDefaults(viewable_width)    600
    set igd_applDefaults(viewable_height)   400
    set igd_applDefaults(disp_nodelabels)   0
    set igd_applDefaults(disp_nodeweights)  1
    set igd_applDefaults(disp_edgeweights)  1
    set igd_applDefaults(node_dash)         ""
    set igd_applDefaults(edge_dash)         ""
    set igd_applDefaults(node_radius)       4
    set igd_applDefaults(interactive_mode)  1
    set igd_applDefaults(mouse_tracking)    1
    set igd_applDefaults(scale_factor)      1
    set igd_applDefaults(nodelabel_font)  -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-*
    set igd_applDefaults(nodeweight_font) -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-*
    set igd_applDefaults(edgeweight_font) -adobe-helvetica-bold-r-normal--11-80-*-*-*-*-*-*

    set igd_applDescList [list canvas_width canvas_height viewable_width \
	    viewable_height disp_nodelabels disp_nodeweights disp_edgeweights \
	    node_dash edge_dash node_radius interactive_mode mouse_tracking \
	    scale_factor nodelabel_font nodeweight_font edgeweight_font]

    # withdraw the wish window
    wm withdraw .
}   

#############################################################################
# Set application defaults. This function could be called from an outside
# application.
#############################################################################

proc Igd_SetApplDefaults { canvas_width canvas_height viewable_width \
	viewable_height disp_nodelabels disp_nodeweights disp_edgeweights \
	node_dash edge_dash node_radius interactive_mode mouse_tracking \
	scale_factor nodelabel_font nodeweight_font edgeweight_font } {

    global igd_applDefaults

    set igd_applDefaults(canvas_width)      $canvas_width
    set igd_applDefaults(canvas_height)     $canvas_height
    set igd_applDefaults(viewable_width)    $viewable_width
    set igd_applDefaults(viewable_height)   $viewable_height
    set igd_applDefaults(disp_nodelabels)   $disp_nodelabels
    set igd_applDefaults(disp_nodeweights)  $disp_nodeweights
    set igd_applDefaults(disp_edgeweights)  $disp_edgeweights
    set igd_applDefaults(node_dash)         $node_dash
    set igd_applDefaults(edge_dash)         $edge_dash
    set igd_applDefaults(node_radius)       $node_radius
    set igd_applDefaults(interactive_mode)  $interactive_mode
    set igd_applDefaults(mouse_tracking)    $mouse_tracking
    set igd_applDefaults(scale_factor)      $scale_factor
    set igd_applDefaults(nodelabel_font)    $nodelabel_font
    set igd_applDefaults(nodeweight_font)   $nodeweight_font
    set igd_applDefaults(edgeweight_font)   $edgeweight_font
}

#############################################################################
# Copy application defaults into window's igd_windowDesc.
#############################################################################

proc Igd_CopyApplDefaultToWindow { window } {

    global igd_applDefaults igd_windowDesc

    foreach option [array names igd_applDefaults] {
	set igd_windowDesc($option,$window) $igd_applDefaults($option)
    }
}

#############################################################################
# Copy from_window's description into to_window's description.
#############################################################################

proc Igd_CopyWindowDesc { to_window from_window } {

    global igd_windowDesc igd_applDescList

    foreach option $igd_applDescList {
	set igd_windowDesc($option,$to_window) \
		$igd_windowDesc($option,$from_window)
    }
}

#############################################################################
# Set window description
#############################################################################

proc Igd_SetWindowDesc { window canvas_width canvas_height viewable_width \
	viewable_height disp_nodelabels disp_nodeweights disp_edgeweights \
	node_dash edge_dash node_radius interactive_mode mouse_tracking \
	scale_factor nodelabel_font nodeweight_font edgeweight_font } {

    global igd_windowDesc

    set igd_windowDesc(canvas_width,$window)      $canvas_width
    set igd_windowDesc(canvas_height,$window)     $canvas_height
    set igd_windowDesc(viewable_width,$window)    $viewable_width
    set igd_windowDesc(viewable_height,$window)   $viewable_height
    set igd_windowDesc(disp_nodelabels,$window)   $disp_nodelabels
    set igd_windowDesc(disp_nodeweights,$window)  $disp_nodeweights
    set igd_windowDesc(disp_edgeweights,$window)  $disp_edgeweights
    set igd_windowDesc(node_dash,$window)         $node_dash
    set igd_windowDesc(edge_dash,$window)         $edge_dash
    set igd_windowDesc(node_radius,$window)       $node_radius
    set igd_windowDesc(interactive_mode,$window)  $interactive_mode
    set igd_windowDesc(mouse_tracking,$window)    $mouse_tracking
    set igd_windowDesc(scale_factor,$window)      $scale_factor
    set igd_windowDesc(nodelabel_font,$window)    $nodelabel_font
    set igd_windowDesc(nodeweight_font,$window)   $nodeweight_font
    set igd_windowDesc(edgeweight_font,$window)   $edgeweight_font
}

#############################################################################
# Set window description and apply at once.
#############################################################################

proc Igd_SetAndExecuteWindowDesc { window canvas_width canvas_height \
	viewable_width 	viewable_height disp_nodelabels disp_nodeweights \
	disp_edgeweights node_dash edge_dash node_radius interactive_mode \
	mouse_tracking scale_factor nodelabel_font nodeweight_font \
	edgeweight_font } {

    global igd_windowDesc

    if { $igd_windowDesc(canvas_width,$window) != $canvas_width || \
	    $igd_windowDesc(canvas_height,$window) != $canvas_height } {
	Igd_ResizeCanvas $window $canvas_width $canvas_height
	set igd_windowDesc(canvas_width,$window)      $canvas_width
	set igd_windowDesc(canvas_height,$window)     $canvas_height
    }

    if { $igd_windowDesc(viewable_width,$window) != $viewable_width || \
	    $igd_windowDesc(viewable_height,$window) != $viewable_height } {
	Igd_ResizeViewableWindow $window $viewable_width $viewable_height
	set igd_windowDesc(viewable_width,$window)      $viewable_width
	set igd_windowDesc(viewable_height,$window)     $viewable_height
    }

    if { $igd_windowDesc(disp_nodelabels,$window) != $disp_nodelabels } {
	if { $disp_nodelabels == 1 } {
	    Igd_DisplayNodelabels $window
	} else {
	    Igd_UndisplayNodelabels $window
	}
	set igd_windowDesc(disp_nodelabels,$window)   $disp_nodelabels
    }
    if { $igd_windowDesc(disp_nodeweights,$window) != $disp_nodeweights } {
	if { $disp_nodeweights == 1 } {
	    Igd_DisplayNodeweights $window
	} else {
	    Igd_UndisplayNodeweights $window
	}
	set igd_windowDesc(disp_nodeweights,$window)  $disp_nodeweights
    }
    if { $igd_windowDesc(disp_edgeweights,$window) != $disp_edgeweights } {
	if { $disp_edgeweights == 1 } {
	    Igd_DisplayEdgeweights $window
	} else {
	    Igd_UndisplayEdgeweights $window
	}
	set igd_windowDesc(disp_edgeweights,$window)  $disp_edgeweights
    }
	
    if { $igd_windowDesc(node_dash,$window) != $node_dash } {
	Igd_ChangeNodeDash $window $node_dash 1
	set igd_windowDesc(node_dash,$window)         $node_dash
    }
    if { $igd_windowDesc(edge_dash,$window) != $edge_dash } {
	Igd_ChangeEdgeDash $window $edge_dash 1
	set igd_windowDesc(edge_dash,$window)         $edge_dash
    }

    if { $igd_windowDesc(node_radius,$window) != $node_radius } {
	Igd_ChangeNodeRadius $window $node_radius 1
	set igd_windowDesc(node_radius,$window)       $node_radius
    }

    if { $igd_windowDesc(interactive_mode,$window) != $interactive_mode } {
	if { $interactive_mode == 1 } {
	    Igd_EnableBindings $window
	} else {
	    Igd_DisableBindings $window
	}
	set igd_windowDesc(interactive_mode,$window)  $interactive_mode
    }

    if { $igd_windowDesc(mouse_tracking,$window) != $mouse_tracking } {
	if { $mouse_tracking == 1 } {
	    Igd_EnableMouseTracking $window 
	} else {
	    Igd_DisableMouseTracking $window
	}  
	set igd_windowDesc(mouse_tracking,$window)  $mouse_tracking
    }

    if { $igd_windowDesc(scale_factor,$window) != $scale_factor } {
	set multiplier \
		[expr double($scale_factor) / $igd_windowDesc(scale_factor,$window)]
	Igd_ScaleGraph $window $multiplier
	set igd_windowDesc(scale_factor,$window) $scale_factor
    }

    if { $igd_windowDesc(nodelabel_font,$window) != $nodelabel_font } {
	Igd_ChangeNodeLabelFont $window $nodelabel_font
	set igd_windowDesc(nodelabel_font,$window)    $nodelabel_font
    }
    if { $igd_windowDesc(nodeweight_font,$window) != $nodeweight_font } {
	Igd_ChangeNodeWeightFont $window $nodeweight_font
	set igd_windowDesc(nodeweight_font,$window)   $nodeweight_font
    }
    if { $igd_windowDesc(edgeweight_font,$window) != $edgeweight_font } {
	Igd_ChangeEdgeWeightFont $window $edgeweight_font
	set igd_windowDesc(edgeweight_font,$window)   $edgeweight_font
    }
}

#############################################################################
# Initialize a new window: set its title, some variables
# corresponding to the window, and add the window identifier to 
# igd_applWindows.
#     window: identifier of the new window for the user
#     title: title of the window
#############################################################################

proc Igd_InitWindow { window title } {

    global igd_windowToplevel igd_windowFromToplevel igd_windowTitle \
	    igd_windowNodes igd_windowNodeNum igd_windowNodeCount \
	    igd_windowEdges igd_windowEdgeNum igd_windowDesc \
	    igd_windowCApplEnabled igd_applWindows igd_applWindowCount \
	    igd_applWindowNum 

    # define the path name of the toplevel window
    set toplevel_name .top$igd_applWindowNum

    # increase igd_applWindowCount and igd_applWindowNum by 1, and add the 
    # window identifier to igd_applWindows
    incr igd_applWindowCount ; incr igd_applWindowNum
    lappend igd_applWindows $window

    # set the variables corresponding to this window
    set igd_windowToplevel($window) $toplevel_name
    set igd_windowFromToplevel($toplevel_name) $window
    set igd_windowTitle($window) $title

    set igd_windowNodes($window) {}
    set igd_windowNodeNum($window) 0
    set igd_windowNodeCount($window) 0
    set igd_windowEdges($window) {}
    set igd_windowEdgeNum($window) 0

    set igd_windowCApplEnabled($window) 0

}

#############################################################################
# Display the application window (define menus, canvas, registers, and
# bindings, mouse tracker).
#     window: identifier of the window
#############################################################################

proc Igd_DisplayWindow { window } {

    global igd_windowDesc igd_windowToplevel igd_windowTitle \
	    igd_windowMouseTrackerID igd_windowCApplEnabled

    # get the toplevel name first
    set toplevel_name $igd_windowToplevel($window)

    # the underlying window is a toplevel frame
    toplevel $toplevel_name -class frame
    wm title $toplevel_name $igd_windowTitle($window)

    # define and pack the children of this frame. the -6 is there b/c 
    # tk adds 6 pixels for the border. -5 bc of scrollbar
    set mbar [frame $toplevel_name.mbar -relief groove -bd 3]
    set c [canvas $toplevel_name.c -relief groove -bd 3 \
	    -highlightthickness 0 \
	    -width [expr $igd_windowDesc(viewable_width,$window) - 6] \
	    -height [expr $igd_windowDesc(viewable_height,$window) - 6] \
	    -xscrollcommand [list $toplevel_name.xscroll set] \
	    -yscrollcommand [list $toplevel_name.yscroll set] \
	    -xscrollincrement 5p -yscrollincrement 5p \
	    -scrollregion [list 0 0 $igd_windowDesc(canvas_width,$window) $igd_windowDesc(canvas_height,$window)] ]
    set xsc [scrollbar $toplevel_name.xscroll -orient horizontal -width 12 \
	    -command [list Igd_my_xscroll $toplevel_name]]
    set ysc [scrollbar $toplevel_name.yscroll -orient vertical -width 12 \
	    -command [list Igd_my_yscroll $toplevel_name]]
    set choice [frame $toplevel_name.choice -relief groove -bd 3]
    set reg [frame $toplevel_name.reg -relief groove -bd 3]
    set msgbar [frame $toplevel_name.msgbar -relief groove -bd 3]

    pack $mbar -side top -fill x
    pack $msgbar $reg $choice $xsc -side bottom -fill x
    pack $ysc -side right -fill y
    pack $c -side top -fill both -expand true

    # create a hidden "dummy" item on the canvas that is going to be 
    # always the lowest item. this way, we will be able to scan thru 
    # the display list easily.
    $c create text -5 -5 -text "!!!" -tags "dummy" -state hidden

    # define and pack the menubuttons in the menubar (mbar)
    menubutton $mbar.file -text File -underline 0 -menu $mbar.file.menu
    menubutton $mbar.window -text Window -underline 0 \
	    -menu $mbar.window.menu
    menubutton $mbar.node -text Nodes -underline 0 \
	    -menu $mbar.node.menu 
    menubutton $mbar.edge -text Edges -underline 0 \
	    -menu $mbar.edge.menu 
    menubutton $mbar.help -text Help -underline 0 -menu $mbar.help.menu
    # this is the button that brings up the copyright message
    button $mbar.copy -text (C) -width 1 \
	    -command "Igd_copyright $toplevel_name"
    pack $mbar.copy -side left
    pack $mbar.file $mbar.window $mbar.node $mbar.edge $mbar.help -side left

    # define the menu items (and their commands) for the four menubuttons
    Igd_set_filemenu $toplevel_name ; Igd_set_windowmenu $toplevel_name
    Igd_set_nodemenu $toplevel_name ; Igd_set_edgemenu $toplevel_name
    Igd_set_helpmenu $toplevel_name

    # enable keyboard shortcuts for the menus
    tk_menuBar $mbar $mbar.file $mbar.window $mbar.nodedge $mbar.help
    # focus $mbar

    # set up mouse tracking gadget
    frame $c.track -relief ridge -borderwidth 1
    label $c.track.x -width 4 -textvariable igd_windowMousePosition(x,$window)
    label $c.track.y -width 4 -textvariable igd_windowMousePosition(y,$window)
    pack $c.track.x $c.track.y -side left

    # set up the radiobuttons in the choice frame
    label $choice.nl -text "Display labels"
    radiobutton $choice.nlyes -text "yes" \
	    -variable igd_windowDesc(disp_nodelabels,$window) \
	    -value 1 -command "Igd_DisplayNodelabels $window"
    radiobutton $choice.nlno -text "no" \
	    -variable igd_windowDesc(disp_nodelabels,$window) \
	    -value 0  -command "Igd_UndisplayNodelabels $window"
    label $choice.nw -text "  node weights"
    radiobutton $choice.nwyes -text "yes" \
	    -variable igd_windowDesc(disp_nodeweights,$window) \
	    -value 1 -command "Igd_DisplayNodeweights $window"
    radiobutton $choice.nwno -text "no" \
	    -variable igd_windowDesc(disp_nodeweights,$window) \
	    -value 0 -command "Igd_UndisplayNodeweights $window"
    label $choice.ew -text "  edge weights"
    radiobutton $choice.ewyes -text "yes" \
	    -variable igd_windowDesc(disp_edgeweights,$window) \
	    -value 1 -command "Igd_DisplayEdgeweights $window"
    radiobutton $choice.ewno -text "no" \
	    -variable igd_windowDesc(disp_edgeweights,$window) \
	    -value 0 -command "Igd_UndisplayEdgeweights $window"

    pack $choice.nl $choice.nlyes $choice.nlno $choice.nw $choice.nwyes \
	    $choice.nwno $choice.ew $choice.ewyes $choice.ewno -side left 
    
    # set up the register display
    set r1 [frame $toplevel_name.reg.r1]
    set r2 [frame $toplevel_name.reg.r2]
    pack $r1 $r2 -side top -fill x
    label $r1.label 
    button $r1.button -text "clear register 1" -borderwidth 1 \
	    -command "Igd_empty_register $toplevel_name 1; \
	    Igd_update_registers $toplevel_name"
    label $r2.label
    button $r2.button -text "clear register 2" -borderwidth 1 \
	    -command "Igd_empty_register $toplevel_name 2; \
	    Igd_update_registers $toplevel_name"
    pack $r1.label $r2.label -side left
    pack $r1.button $r2.button

    # initialize the registers
    Igd_empty_register $toplevel_name 1
    Igd_empty_register $toplevel_name 2
    Igd_update_registers $toplevel_name

    # define the message bar 
    label $msgbar.msg 
    pack $msgbar.msg -side left

    # wait until the window is displayed
    tkwait visibility $c

    # packer might have set the canvas bigger than requested, so resize
    # $c configure -width [expr [winfo width $c] - 6] \
	    -height [expr [winfo height $c] - 6]
    set igd_windowDesc(viewable_width,$window) [winfo width $c]
    set igd_windowDesc(viewable_height,$window) [winfo height $c]
    set canvas_width [Igd_max $igd_windowDesc(canvas_width,$window) \
	    $igd_windowDesc(viewable_width,$window)]
    set canvas_height [Igd_max $igd_windowDesc(canvas_height,$window) \
	    $igd_windowDesc(viewable_height,$window)]
    Igd_ResizeCanvas $window $canvas_width $canvas_height

    # define permanent bindings
    Igd_permanent_bindings $toplevel_name

    # if interactive_mode is enabled, define extra bindings 
    if { $igd_windowDesc(interactive_mode,$window) == 1 } { 
	Igd_EnableBindings $window
    }

    # activate mouse tracking if option is enabled
    if { $igd_windowDesc(mouse_tracking,$window) == 1 } {
	Igd_EnableMouseTracking $window
    }
}

#############################################################################
# Display copyright message if (C) is clicked on.
#############################################################################

proc Igd_copyright { toplevel_name } {

    # the name of the toplevel window containing the copyright 
    # message is $toplevel_name.cpr. 
    set box $toplevel_name.cpr
    if { ![winfo exists $box] } {
	set text "IGD-1.0 Interactive Graph Drawing, Copyright (C) 1996 Marta Eso\n\nIGD-1.0 comes with ABSOLUTELY NO WARRANTY. This is a free software, \nand you are welcome to redistribute it under certain conditions. \nSee the file COPYRIGHT that came with the source code for details.\n"
	Igd_message_box $box "Copyright info" 600 1 $text
    }	
}

#############################################################################
# Create the File menu and add the options.
#############################################################################

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


#############################################################################
# Create the Window menu and add the options.
#############################################################################

proc Igd_set_windowmenu { toplevel_name } {
    
    global igd_windowFromToplevel
    
    set m [menu $toplevel_name.mbar.window.menu -tearoff 0]
    set window $igd_windowFromToplevel($toplevel_name)
    
    $m add command -label "Clone window" \
	    -command "Igd_clone_window $toplevel_name"
    $m add command -label "New window" \
	    -command "Igd_new_window $toplevel_name"

    $m add separator

    $m add command -label "Rename window" \
	    -command "Igd_rename_window $toplevel_name"
    $m add command -label "Resize (viewable) window" \
	    -command "Igd_resize_viewable_window $toplevel_name"
    $m add command -label "Resize canvas" \
	    -command "Igd_resize_canvas $toplevel_name"
    $m add command -label "Default fonts" \
	    -command "Igd_change_fonts $toplevel_name"
    $m add command -label "Default dash patterns" \
	    -command "Igd_change_dash_patterns $toplevel_name"
    $m add command -label "Default node radius" \
	    -command "Igd_change_node_radius $toplevel_name"

    $m add separator

    $m add cascade -label "Interactive mode" -menu $m.sub1 
    $m add cascade -label "Mouse tracking" -menu $m.sub2
    $m add cascade -label "(re)Scale graph" -menu $m.sub3

    $m add separator

    $m add command -label "Erase window" -command "Igd_EraseWindow $window"
    $m add command -label "Quit from window" -command "Igd_QuitWindow $window"
    
    set m1 [menu $m.sub1 -tearoff 0]
    $m1 add radio -label "Enabled" \
	    -variable igd_windowDesc(interactive_mode,$window) \
	    -value 1 -command "Igd_EnableBindings $window"
    $m1 add radio -label "Disabled" \
	    -variable igd_windowDesc(interactive_mode,$window) \
	    -value 0 -command "Igd_DisableBindings $window"

    set m2 [menu $m.sub2 -tearoff 0]
    $m2 add radio -label "Enabled" \
	    -variable igd_windowDesc(mouse_tracking,$window) \
	    -value 1 -command "Igd_EnableMouseTracking $window"
    $m2 add radio -label "Disabled" \
	    -variable igd_windowDesc(mouse_tracking,$window) \
	    -value 0 -command "Igd_DisableMouseTracking $window"

    set m3 [menu $m.sub3 -tearoff 0]
    $m3 add command -label "0.5 x" -command "Igd_ScaleGraph $window 0.5"
    $m3 add command -label "0.66x" -command "Igd_ScaleGraph $window 0.66666"
    $m3 add command -label "1.5 x" -command "Igd_ScaleGraph $window 1.5"
    $m3 add command -label "  2 x" -command "Igd_ScaleGraph $window 2"
    $m3 add command -label "custom scaling" \
	-command "Igd_custom_scale $toplevel_name"
    $m3 add separator
    $m3 add command -label "shrink into window" \
	    -command "Igd_ShrinkIntoWindow $window"
    $m3 add command -label "reset scale" -command "Igd_ResetScale $window"
    
}


#############################################################################
# Create the Nodes menu and add the options.
#############################################################################

proc Igd_set_nodemenu { toplevel_name } {

    set m [menu $toplevel_name.mbar.node.menu -tearoff 0]
    
    $m add command -label "Add node" \
	    -command "Igd_add_node $toplevel_name"
    $m add command -label "Modify node" \
	    -command "Igd_modify_node $toplevel_name"
    $m add command -label "Move node" \
	    -command "Igd_move_node $toplevel_name"
    $m add command -label "Raise node" \
	    -command "Igd_raise_node $toplevel_name"
    $m add command -label "Lower node" \
	    -command "Igd_lower_node $toplevel_name"

    $m add separator

    $m add command -label "Node info" \
	    -command "Igd_node_info $toplevel_name"

    $m add separator

    $m add command -label "Delete node" \
	    -command "Igd_delete_node $toplevel_name"

}

#############################################################################
# Create the Edges menu and add the options.
#############################################################################

proc Igd_set_edgemenu { toplevel_name } {
    
    set m [menu $toplevel_name.mbar.edge.menu -tearoff 0]
    
    $m add command -label "Add edge" \
	    -command "Igd_add_edge $toplevel_name"
    $m add command -label "Modify edge" \
	    -command "Igd_modify_edge $toplevel_name"

    $m add separator

    $m add command -label "Edge info" \
	    -command "Igd_edge_info $toplevel_name"

    $m add separator

    $m add command -label "Delete edge" \
	    -command "Igd_delete_edge $toplevel_name"
}


#############################################################################
# Create the Help menu and add the options.
#############################################################################

proc Igd_set_helpmenu { toplevel_name } {

    set m [menu $toplevel_name.mbar.help.menu -tearoff 0]

    $m add command -label "File menu" \
	    -command "Igd_help $toplevel_name file"
    $m add command -label "Window menu" \
	    -command "Igd_help $toplevel_name window"
    $m add command -label "Nodes menu" \
	    -command "Igd_help $toplevel_name node"
    $m add command -label "Edges menu" \
	    -command "Igd_help $toplevel_name edge"
}

##############################################################################
# Pop up a help window with the file $tag.txt in it.
##############################################################################

proc Igd_help { toplevel_name tag } {

    # the name of the toplevel window containing the help will be
    # $toplevel_name.help$tag. If this window is aready open, do
    # nothing. Otherwise open a help window and display corresponding 
    # text.
    if { ![winfo exists $toplevel_name.help$tag] } {
	set h [toplevel $toplevel_name.help$tag -class frame ]
	wm title $h "Help $tag"
	message $h.msg -bd 3 -relief groove -aspect 500
	frame $h.mbar -bd 1
	pack $h.msg $h.mbar -side top -fill both
	button $h.mbar.done -text "Done" -command "destroy $h"
	pack $h.mbar.done -padx 1m -pady 1m
	
	set file_name [append tag "menu.txt"]
	$h.msg configure -text [read [open $file_name]]
    }
}


#############################################################################
# Set permanent canvas bindings.
#############################################################################

proc Igd_permanent_bindings { toplevel_name } {

    set c $toplevel_name.c

    # Focus is set to the canvas if mouse is over it. Keyboard bindings
    # don't work if this is not set.
    bind $c <Enter> {
	focus %W
    }

    # The variable igd_windowMousePosition follows the mouse
    bind $c <Motion> {
	set window $igd_windowFromToplevel([winfo parent %W])
	set leftperc [lindex [%W xview] 0]
	set topperc [lindex [%W yview] 0]
	set igd_windowMousePosition(x,$window) \
		[expr %x + int($leftperc * $igd_windowDesc(canvas_width,$window))]
	set igd_windowMousePosition(y,$window) \
		[expr %y + int($topperc * $igd_windowDesc(canvas_height,$window))]
    }

    # What happens when the window is resized
    bind $c <Configure> {
	# requested size of the canvas is changed
	# %W configure -width [winfo width %W] -height [winfo height %W]

	# mouse tracker is moved. 
	set window $igd_windowFromToplevel([winfo parent %W])
	if { [info exists igd_windowMouseTrackerID($window)] } {
	    %W coords $igd_windowMouseTrackerID($window) \
		    [expr [winfo width %W] -6] [expr [winfo height %W] -6]
	}
	
	# igd_windowDesc data structure is updated
	set igd_windowDesc(viewable_width,$window) [winfo width %W]
	set igd_windowDesc(viewable_height,$window) [winfo height %W]

	set canvas_width [Igd_max $igd_windowDesc(canvas_width,$window) \
		$igd_windowDesc(viewable_width,$window)]
	set canvas_height [Igd_max $igd_windowDesc(canvas_height,$window) \
		$igd_windowDesc(viewable_height,$window)]
	Igd_ResizeCanvas $window $canvas_width $canvas_height
    }

    # when the mouse enters a node, the node is highlighted
    $c bind node <Enter> {
	# current_item is the widget id of the circle or label the 
	# mouse currently is over
	set current_item [%W find withtag current]
	Igd_node_enter_leave enter %W $current_item [%W gettags $current_item]
    }

    # when the mouse leaves the node, the node is back to its normal state
    $c bind node <Leave> {
	# current_item is the widget id of the circle or label the 
	# mouse currently is over
	set current_item [%W find withtag current]
	Igd_node_enter_leave leave %W $current_item [%W gettags $current_item]
    }
    
    # if the left mouse button is clicked once, put position (node) into reg 1
    bind $c <ButtonPress-1> {
	set current_item [%W find withtag current]
	set reg_number 1
	Igd_one_button_press $reg_number %W %x %y $current_item \
		[%W gettags $current_item]
    } 

    # if the right mouse button is clicked once, put position (node) into reg 2
    bind $c <ButtonPress-3> {
	set current_item [%W find withtag current]
	set reg_number 2
	Igd_one_button_press $reg_number %W %x %y $current_item \
		[%W gettags $current_item]
    } 

    # if a node is clicked on and then "r" is pressed, the node is raised.
    bind $c <ButtonPress-1><KeyPress-r> {
	set current_item [%W find withtag current]
	Igd_keypress_perm r %W $current_item [%W gettags $current_item]
    }

    # if a node is clicked on and then "l" is pressed, the node is lowered
    # under the other nodes
    bind $c <ButtonPress-1><KeyPress-l> {
	set current_item [%W find withtag current]
	Igd_keypress_perm l %W $current_item [%W gettags $current_item]
    }

    # if the ? is pressed over a node, node information is displayed
    bind $c <ButtonPress-1><KeyPress-question> {
	set current_item [%W find withtag current]
	Igd_keypress_perm q %W $current_item [%W gettags $current_item]
    }


}

proc Igd_node_enter_leave { which c current_item taglist } {

    global igd_windowFromToplevel igd_nodeWidgetID igd_nodeFromWidgetID

    set window $igd_windowFromToplevel([winfo parent $c])

    # find out the widget id of the circle and label corresponding to the
    # node
    if { [lsearch $taglist label] >= 0 } {
	# if the current item is a label
	set node $igd_nodeFromWidgetID(label,$window,$current_item)
    } else {
	# if the current item is a circle
	set node $igd_nodeFromWidgetID(circle,$window,$current_item)
    }
    set circle $igd_nodeWidgetID(circle,$window,$node)
    set label $igd_nodeWidgetID(label,$window,$node)


    if { $which == "enter" } {
	$c itemconfigure $circle -fill black
	$c itemconfigure $label -fill yellow
    } else {
	$c itemconfigure $circle -fill yellow
	$c itemconfigure $label -fill black
    }
}

proc Igd_one_button_press { reg_number c x y current_item taglist } {

    global igd_windowFromToplevel igd_windowRegisters igd_nodeFromWidgetID \
	    igd_nodeDesc igd_windowDesc

    set toplevel_name [winfo parent $c]
    set window $igd_windowFromToplevel($toplevel_name)

    set c $toplevel_name.c
    set leftperc [lindex [$c xview] 0]
    set topperc [lindex [$c yview] 0]
    set x [expr $x + int($leftperc * $igd_windowDesc(canvas_width,$window))]
    set y [expr $y + int($topperc * $igd_windowDesc(canvas_height,$window))]

    if { [lsearch $taglist label] >= 0 } {
	# if the current item is a label
	set node $igd_nodeFromWidgetID(label,$window,$current_item)
	set label $igd_nodeDesc(label,$window,$node)
    } elseif { [lsearch $taglist circle] >= 0 } {
	# if the current item is a circle
	set node $igd_nodeFromWidgetID(circle,$window,$current_item)
	set label $igd_nodeDesc(label,$window,$node)
    } else {
	set node "" ; set label ""
    }

    # update register
    set igd_windowRegisters($reg_number,x,$window) $x
    set igd_windowRegisters($reg_number,y,$window) $y
    set igd_windowRegisters($reg_number,label,$window) $label
    set igd_windowRegisters($reg_number,node,$window) $node
    Igd_update_registers $toplevel_name 
}
    

proc Igd_keypress_perm { which_key c current_item taglist } {

    global igd_windowFromToplevel igd_windowRegisters

    set window $igd_windowFromToplevel([winfo parent $c])

    set node $igd_windowRegisters(1,node,$window)

    if { $node != "" } {
	switch -exact -- $which_key {
	    r {	Igd_RaiseNode $window $node }
	    l { Igd_LowerNode $window $node }
	    q { Igd_InfoNode $window $node }
	}
    } else {
	Igd_message_box $toplevel_name.mbox error 500 \
		"\n Need to have a node in register 1 \n\n" 1
    }	
}

#############################################################################
# Display/undisplay node labels.
#############################################################################

proc Igd_DisplayNodelabels { window } {

    global igd_windowToplevel igd_windowNodes igd_nodeWidgetID igd_nodeDesc

    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	$c itemconfigure $igd_nodeWidgetID(label,$window,$node) \
		-text $igd_nodeDesc(label,$window,$node)
    }
    Igd_PrintMsg $window "Node labels are displayed now"
}

proc Igd_UndisplayNodelabels { window } {

    global igd_windowToplevel igd_windowNodes igd_nodeWidgetID

    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	$c itemconfigure $igd_nodeWidgetID(label,$window,$node) -text ""
    }
    Igd_PrintMsg $window "Node labels are withdrawn now"
}


#############################################################################
# Display/undisplay node weights.
#############################################################################

proc Igd_DisplayNodeweights { window } {

    global igd_windowToplevel igd_windowNodes igd_nodeWidgetID igd_nodeDesc

    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
	    $c itemconfigure $igd_nodeWidgetID(weight,$window,$node) \
		    -text $igd_nodeDesc(weight,$window,$node)
	}
    }
    Igd_PrintMsg $window "Node weights are displayed now"
}

proc Igd_UndisplayNodeweights { window } {

    global igd_windowToplevel igd_windowNodes igd_nodeWidgetID

    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
	    $c itemconfigure $igd_nodeWidgetID(weight,$window,$node) -text ""
	}
    }
    Igd_PrintMsg $window "Node weights are withdrawn now"
}


#############################################################################
# Display/undisplay edge weights.
#############################################################################

proc Igd_DisplayEdgeweights { window } {

    global igd_windowToplevel igd_windowEdges igd_edgeWidgetID igd_edgeDesc

    set c $igd_windowToplevel($window).c

    foreach edge $igd_windowEdges($window) {
	if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
	    $c itemconfigure $igd_edgeWidgetID(weight,$window,$edge) \
		    -text $igd_edgeDesc(weight,$window,$edge)
	}
    }
    Igd_PrintMsg $window "Edge weights are displayed now"
}

proc Igd_UndisplayEdgeweights { window } {

    global igd_windowToplevel igd_windowEdges igd_edgeWidgetID

    set c $igd_windowToplevel($window).c

    foreach edge $igd_windowEdges($window) {
	if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
	    $c itemconfigure $igd_edgeWidgetID(weight,$window,$edge) -text ""
	}
    }
    Igd_PrintMsg $window "Edge weights are withdrawn now"
}

#############################################################################
# Update registers from variables igd_windowRegisters. Empty register $which.
#############################################################################

proc Igd_update_registers { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters

    set window $igd_windowFromToplevel($toplevel_name)
    for { set i 1 } { $i <= 2 } { incr i } {
	set text [format \
		"Register %1d:  x: %4s  y: %4s  label: %3s  node id: %3s" $i \
		$igd_windowRegisters($i,x,$window) \
		$igd_windowRegisters($i,y,$window) \
		$igd_windowRegisters($i,label,$window) \
		$igd_windowRegisters($i,node,$window)]

	$toplevel_name.reg.r$i.label configure -text $text
    }
}

proc Igd_empty_register { toplevel_name  which } {

    global igd_windowFromToplevel igd_windowRegisters

    set window $igd_windowFromToplevel($toplevel_name)

    set igd_windowRegisters($which,x,$window) ""
    set igd_windowRegisters($which,y,$window) ""
    set igd_windowRegisters($which,label,$window) ""
    set igd_windowRegisters($which,node,$window) ""
    
}

#############################################################################
# The following two procedures substitute the commands when the scrollbars
# are manipulated. Note that we need to make the same function call as what
# the usual binding would be (eval ...).
#############################################################################

proc Igd_my_xscroll { toplevel_name args} {

    global igd_windowFromToplevel 

    set window $igd_windowFromToplevel($toplevel_name)
    set c $toplevel_name.c
    
    eval [concat $c xview $args]

    Igd_adjust_mouse_tracker $toplevel_name

}

proc Igd_my_yscroll { toplevel_name args } {

    global igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name)
    set c $toplevel_name.c
    
    eval [concat $c yview $args]

    Igd_adjust_mouse_tracker $toplevel_name
}

proc Igd_adjust_mouse_tracker { toplevel_name } {

    global igd_windowFromToplevel igd_windowMouseTrackerID igd_windowDesc

    set window $igd_windowFromToplevel($toplevel_name)
    set c $toplevel_name.c

    if { [info exists igd_windowMouseTrackerID($window)] } {
	set rightperc [lindex [$c xview] 1]
	set bottomperc [lindex [$c yview] 1]
	$c coords $igd_windowMouseTrackerID($window) \
		[expr int($rightperc*$igd_windowDesc(canvas_width,$window))-6]\
		[expr int($bottomperc*$igd_windowDesc(canvas_height,$window))-6]
    }
}