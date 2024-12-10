#############################################################################
# Opens a new window with the same properties (and graph in it) as the 
# current window. This routine sets the window id's and then invokes 
# Igd_CopyWindow which will do the copying.
#     toplevel_name: the toplevel of the window to be copied.
#############################################################################

proc Igd_clone_window { toplevel_name } {

    global igd_windowFromToplevel igd_applWindowNum

    set from_window $igd_windowFromToplevel($toplevel_name)
    set to_window [expr $igd_applWindowNum + 1]

    Igd_CopyWindow $to_window $from_window

    Igd_print_msg $toplevel_name "Window has been cloned."
}
 
#############################################################################
# Create a new window. Prompt the user for the title of the new window. 
#    toplevel_name: the toplevel of the window the function was invoked from
#############################################################################

proc Igd_new_window { toplevel_name } {

    global igd_windowDesc igd_applIntOrEmptyPattern igd_applWindowNum

    set window [expr $igd_applWindowNum + 1]
    Igd_CopyApplDefaultToWindow $window

    # prompt the user for the title of the window
    set entry_length 40
    set arg0 [list "title (optional): " "window $window" $entry_length]
    set window_list [Igd_dialog_box $toplevel_name.ask "New window" $arg0]

    # if cancel was pressed, simply return from this function
    if { $window_list == "CANCEL" } {
	return
    }

    # interpret the list returned
    set title [lindex $window_list 0]

    Igd_InitWindow $window $title
    Igd_DisplayWindow $window

    Igd_print_msg $toplevel_name "New window with title $title has been created."
}

#############################################################################
# Prompts the user for a new title for the window. Invokes renameWindow.
#    toplevel_name: the toplevel of the window the function was invoked from
#############################################################################

proc Igd_rename_window { toplevel_name } {

    global igd_windowFromToplevel igd_windowTitle

    set window $igd_windowFromToplevel($toplevel_name)

    set entry_length 40
    set arg0 [list "new title for window: " $igd_windowTitle($window) \
	    $entry_length]
    set rename_list [Igd_dialog_box $toplevel_name.ask "Rename window" $arg0]
    
    # if cancel was pressed, simply return from this function
    if { $rename_list == "CANCEL" } {
	return
    }
    
    set title [lindex $rename_list 0]
    
    Igd_RenameWindow $window $title
    
    Igd_print_msg $toplevel_name "Window has been renamed to $title."
}

#############################################################################
# Prompts the user for new window width and height. If the user returns 
# the empty string or 0 as a size, the default value from igd_applDefaults 
# is going to be used.
#############################################################################

proc Igd_resize_viewable_window { toplevel_name } {

    global igd_applDefaults igd_applIntOrEmptyPattern \
	    igd_windowFromToplevel igd_windowDesc
    
    set window $igd_windowFromToplevel($toplevel_name)
    
    set entry_length 20
    set arg0 [list "window width (default if 0): " \
	    $igd_windowDesc(viewable_width,$window) $entry_length]
    set arg1 [list "window height (default if 0): " \
	    $igd_windowDesc(viewable_height,$window) $entry_length]
    set resize_list [Igd_dialog_box $toplevel_name.ask \
	    "Resize (viewable) window" $arg0 $arg1]
    
    # if cancel was pressed, simply return from this function
    if { $resize_list == "CANCEL" } {
	return
    }

    set viewable_width [lindex $resize_list 0]
    set viewable_height [lindex $resize_list 1]
    
    # if the canvas sizes are not integers, give error message and return
    if { [regexp -- $igd_applIntOrEmptyPattern $viewable_width] == 0 || \
	    [regexp -- $igd_applIntOrEmptyPattern $viewable_height] == 0 } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n    Couldn't resize viewable window: \n \
		  Window width and height must be integers!\n"
	return
    }
    
    if { $viewable_width == "" || $viewable_width == 0 } { 
	set viewable_width $igd_applDefaults(viewable_width) 
    }
    if { $viewable_height == "" || $viewable_height == 0 } { 
	set viewable_height $igd_applDefaults(viewable_height)
    }
    
    Igd_ResizeViewableWindow $window $viewable_width $viewable_height

    Igd_print_msg $toplevel_name \
	    "Window has been resized to $viewable_width by $viewable_height"
}

#############################################################################
# Prompts the user for new canvas width and height. 
# If the user returns the empty string or 0 as a size, the default value 
# from igd_applDefaults is going to be used.
#############################################################################

proc Igd_resize_canvas { toplevel_name } {

    global igd_applDefaults igd_applIntOrEmptyPattern \
	    igd_windowFromToplevel igd_windowDesc
    
    set window $igd_windowFromToplevel($toplevel_name)
    
    set entry_length 20
    set arg0 [list "canvas width (default if 0): " \
	    $igd_windowDesc(canvas_width,$window) $entry_length]
    set arg1 [list "canvas height (default if 0): " \
	    $igd_windowDesc(canvas_height,$window) $entry_length]
    set resize_list [Igd_dialog_box $toplevel_name.ask "Resize window" \
	    $arg0 $arg1]
    
    # if cancel was pressed, simply return from this function
    if { $resize_list == "CANCEL" } {
	return
    }

    set canvas_width [lindex $resize_list 0]
    set canvas_height [lindex $resize_list 1]
    
    # if the canvas sizes are not integers, give error message and return
    if { [regexp -- $igd_applIntOrEmptyPattern $canvas_width] == 0 || \
	    [regexp -- $igd_applIntOrEmptyPattern $canvas_height] == 0 } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n      Couldn't resize canvas: \n \
		  Canvas width and height must be integers!\n"
	return
    }
    
    if { $canvas_width == "" || $canvas_width == 0 } { 
	set canvas_width $igd_applDefaults(canvas_width) 
    }
    if { $canvas_height == "" || $canvas_height == 0 } { 
	set canvas_height $igd_applDefaults(canvas_height)
    }
    
    # canvas size cannot be smaller than the size of the viewable window
    set canvas_width [expr \
	 [Igd_max $canvas_width $igd_windowDesc(viewable_width,$window)]]
    set canvas_height [expr \
	 [Igd_max $canvas_height $igd_windowDesc(viewable_height,$window)]]

    Igd_ResizeCanvas $window $canvas_width $canvas_height

    Igd_print_msg $toplevel_name \
	    "Window has been resized to $canvas_width by $canvas_height"
}

#############################################################################
# Prompts the user for new fonts used for node labels/weights and edge
# weights. If an entry is left empty, the default from igd_applDefaults
# is used.
#############################################################################

proc Igd_change_fonts { toplevel_name } {

    global igd_applDefaults igd_applSpacesPattern igd_applCheckFonts\
	    igd_windowFromToplevel igd_windowDesc 
    
    set window $igd_windowFromToplevel($toplevel_name)
    
    set entry_length 40
    set arg0 [list "font used for node labels (default if none): " \
	    $igd_windowDesc(nodelabel_font,$window) $entry_length]
    set arg1 [list "font used for node weights (default if none): " \
	    $igd_windowDesc(nodeweight_font,$window) $entry_length]
    set arg2 [list "font used for edge weights (default if none): " \
	    $igd_windowDesc(edgeweight_font,$window) $entry_length]
    set font_list [Igd_dialog_box $toplevel_name.ask "Change fonts" \
	    $arg0 $arg1 $arg2]
    
    
    # if cancel was pressed, simply return from this function
    if { $font_list == "CANCEL" } {
	return
    }
    
    set nodelabelfont [lindex $font_list 0]
    set nodeweightfont [lindex $font_list 1]
    set edgeweightfont [lindex $font_list 2]
    
    if { [regexp -- $igd_applSpacesPattern $nodelabelfont] } {
	set nodelabelfont $igd_applDefaults(nodelabel_font) 
    }
    if { [regexp -- $igd_applSpacesPattern $nodeweightfont] } {
	set nodeweightfont $igd_applDefaults(nodeweight_font) 
    }
    if { [regexp -- $igd_applSpacesPattern $edgeweightfont] } {
	set edgeweightfont $igd_applDefaults(edgeweight_font) 
    }
    
    if { $igd_applCheckFonts } {
	if { [Igd_CheckFont $window $nodelabelfont] } {
	    if { $nodelabelfont != $igd_windowDesc(nodelabel_font,$window) } {
		Igd_ChangeNodeLabelFont $window $nodelabelfont
		Igd_print_msg $toplevel_name "Node label font has been\
			changed to $nodelabelfont"
	    }
	}
	if { [Igd_CheckFont $window $nodeweightfont] } {
	    if { $nodeweightfont != $igd_windowDesc(nodeweight_font,$window)} {
		Igd_ChangeNodeWeightFont $window $nodeweightfont
		Igd_print_msg $toplevel_name "Node weight font has been\
			changed to $nodeweightfont"
	    }
	}
	if { [Igd_CheckFont $window $edgeweightfont] } {
	    if { $edgeweightfont != $igd_windowDesc(edgeweight_font,$window)} {
		Igd_ChangeEdgeWeightFont $window $edgeweightfont
		Igd_print_msg $toplevel_name "Edge weight font has been\
			changed to $edgeweightfont"
	    }
	}
    } else {
	if { $nodelabelfont != $igd_windowDesc(nodelabel_font,$window) } {
	    Igd_ChangeNodeLabelFont $window $nodelabelfont
	    Igd_print_msg $toplevel_name "Node label font has been\
		    changed to $nodelabelfont"
	}
	if { $nodeweightfont != $igd_windowDesc(nodeweight_font,$window) } {
	    Igd_ChangeNodeWeightFont $window $nodeweightfont
	    Igd_print_msg $toplevel_name "Node weight font has been\
		    changed to $nodeweightfont"
	}
	if { $edgeweightfont != $igd_windowDesc(edgeweight_font,$window) } {
	    Igd_ChangeEdgeWeightFont $window $edgeweightfont
	    Igd_print_msg $toplevel_name "Edge weight font has been\
		    changed to $edgeweightfont"
	}
    }
}


#############################################################################
# Prompts the user for new dash patterns used for the outline of nodes
# and edges. The user controls whether the new default dash patterns will be 
# applied to already existing nodes / edges or not.
#############################################################################

proc Igd_change_dash_patterns { toplevel_name } {
    
    global igd_windowFromToplevel igd_windowDesc
    
    set window $igd_windowFromToplevel($toplevel_name)

    set entry_length 20
    set arg0 [list entry "new node dash pattern: " \
	    $igd_windowDesc(node_dash,$window) $entry_length]
    set arg1 [list radio "  apply to existing nodes? " 0 [list no yes]]
    set arg2 [list entry "new edge dash pattern: " \
	    $igd_windowDesc(edge_dash,$window) $entry_length]
    set arg3 [list radio "  apply to existing edges? " 0 [list no yes]]
    set dash_list [Igd_dialog_box2 $toplevel_name.ask "Change dash patterns" \
	    $arg0 $arg1 $arg2 $arg3]
    
    # if cancel was pressed, simply return from this function
    if { $dash_list == "CANCEL" } {
	return
    }
    
    set nodedash [lindex $dash_list 0]
    set apply_to_nodes [lindex $dash_list 1]
    set edgedash [lindex $dash_list 2]
    set apply_to_edges [lindex $dash_list 3]
    
    if { [Igd_ValidDashPattern $window $nodedash] && \
	    ($apply_to_nodes || $nodedash != \
	    $igd_windowDesc(node_dash,$window))} {
	Igd_ChangeNodeDash $window $nodedash $apply_to_nodes
	Igd_print_msg $toplevel_name "Changed and/or applied to all nodes the\
		new dash pattern $nodedash"
    }
    
    if { [Igd_ValidDashPattern $window $edgedash] && \
	    ($apply_to_edges || $edgedash != \
	    $igd_windowDesc(edge_dash,$window))} {
	Igd_ChangeEdgeDash $window $edgedash $apply_to_edges
	Igd_print_msg $toplevel_name "Changed and/or applied to all edges the\
		new dash pattern $edgedash"
    }
}


#############################################################################
# Prompts the user for new node radius. The user controls whether the new 
# default node radius will be applied to already existing nodes or not. If the 
# entry is left empty, the default from applDefaults is going to be used.
#############################################################################

proc Igd_change_node_radius { toplevel_name } {

    global igd_windowFromToplevel igd_windowDesc \
	    igd_applIntPattern igd_applSpacesPattern igd_applDefaults

    set window $igd_windowFromToplevel($toplevel_name)

    # prompt the user for the new radius
    set entry_length 20
    set arg0 [list entry "new node radius (default if none): " \
	    $igd_windowDesc(node_radius,$window) $entry_length]
    set arg1 [list radio "  apply to existing nodes? " 0 [list no yes]]
    set radius_list [Igd_dialog_box2 $toplevel_name.ask "Change node radius" \
	    $arg0 $arg1]

    # if cancel was pressed, simply return from this function
    if { $radius_list == "CANCEL" } {
	return
    }

    set new_radius [lindex $radius_list 0]
    set apply_to_nodes [lindex $radius_list 1]

    if { [regexp -- $igd_applSpacesPattern $new_radius] } {
	# if the entry is left empty
	set new_radius $igd_applDefaults(node_radius)
    }

    # if the new radius is not an integer, give error message and return
    if { [regexp -- $igd_applIntPattern $new_radius] == 0 } {
	Igd_message_box $toplevel_name.mbox error 500 1\
		"\n  Invalid radius! \n \
		   Radius must be integer.  "
	return
    }

    if { $apply_to_nodes || \
	    $new_radius != $igd_windowDesc(node_radius,$window) } {
	Igd_ChangeNodeRadius $window $new_radius $apply_to_nodes
	Igd_print_msg $toplevel_name "Changed and/or applied to all the nodes\
		the new radius $new_radius"
    }
}

#############################################################################
# Scale canvas and graph by multiplier. The canvas is resized and
# every node of the graph is moved appropriately (edges are moved along
# the nodes). 
#############################################################################

proc Igd_ScaleGraph { window multiplier } {

    global igd_windowToplevel igd_windowDesc igd_windowMouseTrackerID \
	    igd_windowNodes igd_nodeCoord

    set c $igd_windowToplevel($window).c
    set toplevel_name $igd_windowToplevel($window)

    if { $multiplier != 1 } {
	
	set igd_windowDesc(scale_factor,$window) \
		[expr $igd_windowDesc(scale_factor,$window) * $multiplier]

	# reset the size of the canvas (mouse tracker will be moved 
	# automatically) and move every node (edges will be moved along)
	if { $multiplier > 1 } {
	    set canvas_width [expr int($igd_windowDesc(canvas_width,$window) * $multiplier)]
	    set canvas_height [expr  int($igd_windowDesc(canvas_height,$window) * $multiplier)]
	    Igd_ResizeCanvas $window $canvas_width $canvas_height
	    foreach node $igd_windowNodes($window) {
		Igd_MoveNode $window $node \
			[expr int(($multiplier-1)*$igd_nodeCoord(x,$window,$node))]\
			[expr int(($multiplier-1)*$igd_nodeCoord(y,$window,$node))]
	    }
	} else {
	    set canvas_width [Igd_max [expr int($igd_windowDesc(canvas_width,$window) * $multiplier)] $igd_windowDesc(viewable_width,$window)]
	    set canvas_height [Igd_max [expr int($igd_windowDesc(canvas_height,$window) * $multiplier)] $igd_windowDesc(viewable_height,$window)]
	    Igd_ResizeCanvas $window $canvas_width $canvas_height
	    foreach node $igd_windowNodes($window) {
		Igd_MoveNode $window $node \
		       [expr -int((1-$multiplier)*$igd_nodeCoord(x,$window,$node))]\
		       [expr -int((1-$multiplier)*$igd_nodeCoord(y,$window,$node))]
	    }
	}

	Igd_PrintMsg $window "Enlarged picture by the factor of $multiplier."
	
    }
}

#############################################################################
# Prompts the user for a scaling factor. The graph and the canvas will
# be scaled from the origin. If the entry is left empty, the graph is
# not scaled. 
#############################################################################

proc Igd_custom_scale { toplevel_name } {

    global igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name) 
    
    set multiplier 1
    set entry_length 15
    set arg0 [list "Enlarge picture by the factor of: " $multiplier \
	    $entry_length]
    set scale_list [Igd_dialog_box $toplevel_name.ask "Custom scaling" $arg0]

    # if cancel was pressed, simply return from this function
    if { $scale_list == "CANCEL" } {
	return
    }

    set multiplier [lindex $scale_list 0]

    if { [regexp -- $igd_applSpacesPattern $multiplier] } {
	# if the entry is left empty
	set mutiplier 1
    }

    Igd_ScaleGraph $window $multiplier
}

#############################################################################
# Canvas is shrinked to fit into viewable window.
#############################################################################

proc Igd_ShrinkIntoWindow { window } {

    global igd_windowDesc

    set mult_w [expr double($igd_windowDesc(viewable_width,$window)) / $igd_windowDesc(canvas_width,$window)]
    set mult_h [expr double($igd_windowDesc(viewable_height,$window)) / $igd_windowDesc(canvas_height,$window)]

    set multiplier [Igd_min $mult_w $mult_h]

    Igd_ScaleGraph $window $multiplier

}

#############################################################################
# Scale canvas and graph back to their original sizes.
#############################################################################

proc Igd_ResetScale { window } {

    global igd_windowDesc

    if { $igd_windowDesc(scale_factor,$window) != 1 } {
	set multiplier [expr double(1) / $igd_windowDesc(scale_factor,$window)]
	Igd_ScaleGraph $window $multiplier
    }
}

#############################################################################
# Erase the contents of the window. 
#############################################################################

proc Igd_EraseWindow { window } {

    global igd_windowNodes igd_windowNodeNum igd_windowNodeCount \
	    igd_windowEdges igd_windowEdgeNum igd_windowRegisters \
	    igd_windowToplevel

    # first delete all the nodes, this will delete the edges also.
    foreach node $igd_windowNodes($window) {
	Igd_DeleteNode $window $node
    }

    # igd_windowNodes and igd_windowEdges are empty already, 
    # and igd_windowNodeCount is 0
    set igd_windowNodeNum($window) 0
    set igd_windowEdgeNum($window) 0

    # empty the registers.
    Igd_empty_register $igd_windowToplevel($window) 1
    Igd_empty_register $igd_windowToplevel($window) 2
    Igd_update_registers $igd_windowToplevel($window) 

    Igd_PrintMsg $window "Erased window"

}

#############################################################################
# Destroy the current application window. (First, this process  erases the 
# contents of window so that unnecessary data is not kept around.)
#############################################################################

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


#############################################################################
# Copy the window from_window into to_window (i.e. copy the defaults,
# the graph and the contents of the registers).
#############################################################################

proc Igd_CopyWindow { to_window from_window } {

    global igd_windowTitle

    # copy the window description to the new window
    Igd_CopyWindowDesc $to_window $from_window
    # initialize the new window
    Igd_InitWindow $to_window $igd_windowTitle($from_window)
    # display the new window
    Igd_DisplayWindow $to_window
    # copy the graph from from_window's canvas to to_window's canvas
    Igd_CopyGraph $to_window $from_window
    # copy the contents of the registers
    Igd_CopyRegisters $to_window $from_window
}    

#############################################################################
# Copy the graph from from_window's canvas to to_window's canvas. All the
# nodes and edges are copied and their relative order in the display list
# is observed.
#############################################################################

proc Igd_CopyGraph { to_window from_window } {

    global igd_windowNodes igd_windowEdges igd_windowToplevel igd_windowDesc \
	    igd_nodeCoord igd_nodeWidgetID igd_nodeDesc igd_nodeFromWidgetID \
	    igd_edgeEnds igd_edgeWidgetID igd_edgeDesc igd_edgeFromWidgetID

    set from_c $igd_windowToplevel($from_window).c
    set to_c $igd_windowToplevel($to_window).c

    foreach node $igd_windowNodes($from_window) {
	set tmp "$from_window,$node"
	Igd_MakeNode $to_window $node \
		$igd_nodeCoord(x,$tmp) $igd_nodeCoord(y,$tmp) \
		$igd_nodeDesc(label,$tmp) $igd_nodeDesc(dash,$tmp) \
		$igd_nodeDesc(radius,$tmp)
	if { [info exists igd_nodeDesc(weight,$tmp)] } {
	    Igd_MakeNodeWeight $to_window $node $igd_nodeDesc(weight,$tmp)
	}
    }

    foreach edge $igd_windowEdges($from_window) {
	set tmp "$from_window,$edge"
	Igd_MakeEdge $to_window $edge \
		$igd_edgeEnds(tail,$tmp) $igd_edgeEnds(head,$tmp) \
		$igd_edgeDesc(dash,$tmp)
	if { [info exists igd_edgeDesc(weight,$tmp)] } {
	    Igd_MakeEdgeWeight $to_window $edge $igd_edgeDesc(weight,$tmp)
	}
    }
    
    # need to keep the same order of items as on the original picture.
    # first read out the display list
    set node_list [Igd_NodeOrderInDisplayList $from_window]
    set edge_list [Igd_EdgeOrderInDisplayList $from_window]

    # now put the items on to_c in the same order
    foreach edge $edge_list {
	$to_c raise $igd_edgeWidgetID(line,$to_window,$edge)
	if { [info exists igd_edgeWidgetID(weight,$to_window,$edge)] } {
	    $to_c raise $igd_edgeWidgetID(weight,$to_window,$edge)
	}
    }
    foreach node $node_list {
	$to_c raise $igd_nodeWidgetID(circle,$to_window,$node)
	$to_c raise $igd_nodeWidgetID(label,$to_window,$node)
	if { [info exists igd_nodeWidgetID(weight,$to_window,$node)] } {
	    $to_c raise $igd_nodeWidgetID(weight,$to_window,$node)
	}
    }
}

#############################################################################
# Copy the contents of from_window's register into to_window's register.
#############################################################################

proc Igd_CopyRegisters { to_window from_window } {

    global igd_windowRegisters igd_windowToplevel

    for { set i 1 } { $i <= 2 } { incr i } {
	set igd_windowRegisters($i,x,$to_window) \
		$igd_windowRegisters($i,x,$from_window)
	set igd_windowRegisters($i,y,$to_window) \
		$igd_windowRegisters($i,y,$from_window)
	set igd_windowRegisters($i,label,$to_window) \
		$igd_windowRegisters($i,label,$from_window)
	set igd_windowRegisters($i,node,$to_window) \
		$igd_windowRegisters($i,node,$from_window)
    }
    Igd_update_registers $igd_windowToplevel($to_window)
}

#############################################################################
# Rename window. The new title is going to be title.
#############################################################################

proc Igd_RenameWindow { window title } {

    global igd_windowToplevel igd_windowTitle

    set toplevel_name $igd_windowToplevel($window)
    set igd_windowTitle($window) $title

    wm title $toplevel_name $title
}

#############################################################################
# Resize viewable window. The frame containing the canvas is resized, this 
# triggers a configure event, which is going to set the canvas size and move 
# the mouse tracker device (if any); see the permanent binding for details.
#############################################################################

proc Igd_ResizeViewableWindow { window viewable_width viewable_height } {

    global igd_windowToplevel igd_windowDesc

    set toplevel_name $igd_windowToplevel($window)
    
    # Resize the frame of the toplevel: compute how much bigger the toplevel
    # is than the window, and add this amount when resizing.
    # The window size in igd_windowDesc will be updated by the binding.

    set horiz_diff [expr [winfo width $toplevel_name] - \
	    $igd_windowDesc(viewable_width,$window)]
    set vert_diff [expr [winfo height $toplevel_name] - \
	    $igd_windowDesc(viewable_height,$window)]

    wm geometry $toplevel_name \
      [expr $viewable_width + $horiz_diff]x[expr $viewable_height + $vert_diff]

    tkwait variable igd_windowDesc(viewable_height,$window)

    Igd_adjust_mouse_tracker $toplevel_name
}

#############################################################################
# Resize canvas. 
#############################################################################

proc Igd_ResizeCanvas { window canvas_width canvas_height } {

    global igd_windowToplevel igd_windowDesc

    set toplevel_name $igd_windowToplevel($window)
    
    # the new canvas size will be the maximum of the window size and the
    # given canvas sizes...
    set igd_windowDesc(canvas_width,$window) $canvas_width
    set igd_windowDesc(canvas_height,$window) $canvas_height

    $toplevel_name.c configure \
	    -scrollregion [list 0 0 $canvas_width $canvas_height]

    Igd_adjust_mouse_tracker $toplevel_name
}

#############################################################################
# Change the font used in node labels for all nodes currently displayed, and
# set the default font to new_font.
#############################################################################

proc Igd_ChangeNodeLabelFont { window new_font } {

    global igd_windowToplevel igd_windowNodes igd_windowDesc igd_nodeWidgetID

    set igd_windowDesc(nodelabel_font,$window) $new_font
    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	$c itemconfigure $igd_nodeWidgetID(label,$window,$node) -font $new_font
    }
}


#############################################################################
# Change the font used in node weights for all nodes weights currently 
# displayed, and set the default font to new_font.
#############################################################################

proc Igd_ChangeNodeWeightFont { window new_font } {

    global igd_windowToplevel igd_windowNodes igd_windowDesc igd_nodeWidgetID

    set igd_windowDesc(nodeweight_font,$window) $new_font
    set c $igd_windowToplevel($window).c

    foreach node $igd_windowNodes($window) {
	if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
	    $c itemconfigure $igd_nodeWidgetID(weight,$window,$node) \
		    -font $new_font
	}
    }
}

#############################################################################
# Change the font used in edge weights for all edge weights currently 
# displayed, and set the default font to new_font.
#############################################################################

proc Igd_ChangeEdgeWeightFont { window new_font } {

    global igd_windowToplevel igd_windowEdges igd_windowDesc igd_edgeWidgetID

    set igd_windowDesc(edgeweight_font,$window) $new_font
    set c $igd_windowToplevel($window).c

    foreach edge $igd_windowEdges($window) {
	if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
	    $c itemconfigure $igd_edgeWidgetID(weight,$window,$edge) \
		    -font $new_font
	}
    }
}

#############################################################################
# Change the default dash pattern for nodes. If apply_to_nodes is set, change
# the dash patterns of all nodes currently displayed on the canvas to the 
# new value.
#############################################################################

proc Igd_ChangeNodeDash { window new_dash apply_to_nodes } {
    
    global igd_windowDesc igd_windowNodes

    set igd_windowDesc(node_dash,$window) $new_dash

    if { $apply_to_nodes } {
	foreach node $igd_windowNodes($window) {
	    Igd_ChangeOneNodeDash $window $node $new_dash
	}
    }
}

##############################################################################
# Change the default dash pattern for edges. If apply_to_edges is set, change
# the dash patterns of all edges currently displayed on the canvas to the 
# new value.
############################################################################

proc Igd_ChangeEdgeDash { window new_dash apply_to_edges } {
    
    global igd_windowDesc igd_windowEdges

    set igd_windowDesc(edge_dash,$window) $new_dash

    if { $apply_to_edges } {
	foreach edge $igd_windowEdges($window) {
	    Igd_ChangeOneEdgeDash $window $edge $new_dash
	}
    }
}

#############################################################################
# Change the default radius for nodes. If apply_to_nodes is set, change the
# radii of all nodes currently displayed on the canvas to the new value.
#############################################################################

proc Igd_ChangeNodeRadius { window new_radius apply_to_nodes } {
    
    global igd_windowDesc igd_windowNodes

    set igd_windowDesc(node_radius,$window) $new_radius

    if { $apply_to_nodes } {
	foreach node $igd_windowNodes($window) {
	    Igd_ChangeOneNodeRadius $window $node $new_radius
	}
    }
}


#############################################################################
# Enable/disable additional bindings that let the user add and delete
# nodes, add edges, drag the nodes with some simple mouse actions. 
#############################################################################

proc Igd_EnableBindings { window } {

    global igd_windowToplevel igd_windowDesc

    set c $igd_windowToplevel($window).c

    # put down a node of default label, outline and radius at the 
    # position the mouse is pointing at if left mouse button is pressed twice
    bind $c <Double-ButtonPress-1> {
	Igd_double_button_one [winfo parent %W]
    }

    # connect two nodes that are in the registers if the right mouse button 
    # is pressed twice over a node
    bind $c <Double-ButtonPress-3> {
	Igd_double_button_three [winfo parent %W]
    }

    # pressing "d" over a node will delete it
    bind $c <ButtonPress-1><KeyPress-d> {
	Igd_keypress_d [winfo parent %W]
    }

    # move nodes by dragging them with the middle mouse button
    bind $c <ButtonPress-2> {
	set currentX %x
	set currentY %y
    }

    $c bind node <B2-Motion> {
	set current_item [%W find withtag current]
	Igd_button_two_motion %W $current_item [%W gettags $current_item] %x %y
    }
}

#############################################################################

proc Igd_DisableBindings { window } {

    global igd_windowToplevel

    set c $igd_windowToplevel($window).c

    bind $c <Double-ButtonPress-1> {}
    bind $c <Double-ButtonPress-3> {}
    bind $c <ButtonPress-1><KeyPress-d> {}
    bind $c <ButtonPress-2> {}
    $c bind node <B2-Motion> {}
}

#############################################################################
# This function is executed when the left mouse button is pressed twice 
# over the canvas. A node of default label, outline and radius is placed 
# to the position the mouse is pointing at.
#############################################################################

proc Igd_double_button_one { toplevel_name } {
    
    global igd_windowFromToplevel igd_windowRegisters igd_windowDesc \
	    igd_windowNodeNum

    set window $igd_windowFromToplevel($toplevel_name)

    set node [expr $igd_windowNodeNum($window) + 1]
    set label $node

    Igd_MakeNode $window $node $igd_windowRegisters(1,x,$window) \
	    $igd_windowRegisters(1,y,$window) $label \
	    $igd_windowDesc(node_dash,$window) \
	    $igd_windowDesc(node_radius,$window)

    set igd_windowRegisters(1,label,$window) $label
    set igd_windowRegisters(1,node,$window) $node
    Igd_update_registers $toplevel_name
}

#############################################################################
# This function is executed when the right mouse button is pressed twice over 
# the canvas. The two nodes in the registers (if any) are connected with 
# an edge.
#############################################################################

proc Igd_double_button_three { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_windowEdgeNum \
	    igd_windowDesc

    set window $igd_windowFromToplevel($toplevel_name)

    set tail $igd_windowRegisters(1,node,$window)
    set head $igd_windowRegisters(2,node,$window)

    if { $tail != "" && $head != "" } {
	set edge [expr $igd_windowEdgeNum($window) + 1]
	Igd_MakeEdge $window $edge $tail $head \
		$igd_windowDesc(edge_dash,$window)
    } else {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Need to have nodes in both registers \n \n"
    }
}

#############################################################################
# This function is executed when the key d is pressed over a node. The node 
# is deleted from the graph (with all edges adjacent to it).
#############################################################################

proc Igd_keypress_d { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters

    set window $igd_windowFromToplevel($toplevel_name)

    set node $igd_windowRegisters(1,node,$window)

    if { $node != "" } {
	Igd_DeleteNode $window $node
	set igd_windowRegisters(1,node,$window) ""
	set igd_windowRegisters(1,label,$window) ""
	Igd_update_registers $toplevel_name
	if { $igd_windowRegisters(2,node,$window) == $node } {
	    set igd_windowRegisters(2,node,$window) ""
	    set igd_windowRegisters(2,label,$window) ""
	    Igd_update_registers $toplevel_name
	}
    } else {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Need to have a node in register 1 \n\n"
    }
}

#############################################################################
# This function is executed when the mouse is dragged while the middle
# mouse button is pressed down. The node under the mouse (if any) is
# dragged along with the mouse. 
#############################################################################

proc Igd_button_two_motion { c current_item taglist x y} {

    global igd_windowFromToplevel igd_nodeFromWidgetID currentX currentY \
	    igd_windowRegisters

    set toplevel_name [winfo parent $c]
    set window $igd_windowFromToplevel($toplevel_name)

    # find out the widget id of the circle and label corresponding to the
    # node
    if { [lsearch $taglist label] >= 0 } {
	# if the current item is a label
	set node $igd_nodeFromWidgetID(label,$window,$current_item)
    } else {
	# if the current item is a circle
	set node $igd_nodeFromWidgetID(circle,$window,$current_item)
    }
    
    Igd_MoveNode $window $node [expr $x - $currentX] [expr $y - $currentY]
    set currentX $x ; set currentY $y

    # if the node is in any of the registers, modify the position stored 
    # in the register
    if { $igd_windowRegisters(1,node,$window) == $node } {
	set igd_windowRegisters(1,x,$window) $x
	set igd_windowRegisters(1,y,$window) $y
    }
    if { $igd_windowRegisters(2,node,$window) == $node } {
	set igd_windowRegisters(2,x,$window) $x
	set igd_windowRegisters(2,y,$window) $y
    }
    Igd_update_registers $toplevel_name    
}

#############################################################################
# Enable/disable the mouse tracker gadget on window's canvas. The mouse 
# tracker is placed into the lower-right corner of the canvas.
#############################################################################

proc Igd_EnableMouseTracking { window } {

    global igd_windowToplevel igd_windowDesc \
	    igd_windowMouseTrackerID igd_windowMousePosition \
    
    set c $igd_windowToplevel($window).c

    # give dummy values for the variables in the mouse tracker so that 
    # the gadget is shown even if the mouse hasn't been over the canvas yet.
    set igd_windowMousePosition(x,$window) ""
    set igd_windowMousePosition(y,$window) ""

    # the -6 is there to leave some space between the corner of the canvas 
    # and the corner of the gadget.
    set mouse_id [$c create window \
	    [expr $igd_windowDesc(viewable_width,$window) - 6 ] \
	    [expr $igd_windowDesc(viewable_height,$window) - 6 ] -anchor se \
	    -tags "tracker" -window $c.track ]
    
    # place the mouse to be the second in the display list (after the dummy)
    $c lower $mouse_id
    $c raise $mouse_id dummy

    set igd_windowMouseTrackerID($window) $mouse_id

}

#############################################################################

proc Igd_DisableMouseTracking { window } {

    global igd_windowToplevel igd_windowMouseTrackerID igd_windowMousePosition

    set c $igd_windowToplevel($window).c

    $c delete $igd_windowMouseTrackerID($window)

    unset igd_windowMousePosition(x,$window) \
	    igd_windowMousePosition(y,$window) \
	    igd_windowMouseTrackerID($window)
}

