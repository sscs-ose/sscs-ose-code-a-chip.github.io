#############################################################################
# Pops up a dialog window to get the description of a new node from the 
# user. If there is a position in Register 1, then it will be suggested 
# as position for the new node. Also, the default radius, dash and the id 
# of the node as label are displayed in the corresponding entries.
# If invalid coordinates are given, the node will not be displayed.
#############################################################################

proc Igd_add_node { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_windowDesc \
	    igd_windowNodeNum igd_applIntPattern igd_applIntOrEmptyPattern \
	    igd_applDashPattern igd_applSpacesPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a position in the register, set the coordinates of the 
    # new node to that.
    if { $igd_windowRegisters(1,x,$window) != "" } {
	set old_x $igd_windowRegisters(1,x,$window)
	set old_y $igd_windowRegisters(1,y,$window)
    } else {
	set old_x "" ; set old_y ""
    }

    # the node identifier will be igd_windowNodeNum+1, variable will be 
    # incremented in Igd_MakeNode
    set node [expr $igd_windowNodeNum($window) + 1]
    # set the label to be the same as the node identifier
    set label $node
    # set dash and radius to be the defaults
    set dash $igd_windowDesc(node_dash,$window)
    set radius $igd_windowDesc(node_radius,$window)

    # call the dialog box
    set entry_length 20
    set arg0 [list "x coord (required): " $old_x $entry_length]
    set arg1 [list "y coord (required): " $old_y $entry_length]
    set arg2 [list "weight (optional): " "" $entry_length]
    set arg3 [list "label (optional): " $label $entry_length]
    set arg4 [list "dash pattern (optional): " $dash $entry_length]
    set arg5 [list "radius (optional): " $radius $entry_length]
    set new_node_list [Igd_dialog_box $toplevel_name.ask "Add node" \
	    $arg0 $arg1 $arg2 $arg3 $arg4 $arg5]

    # if cancel was pressed, simply return from this function
    if { $new_node_list == "CANCEL" } {
	return
    }

    # otherwise interpret the list returned
    set x [lindex $new_node_list 0] ; set y [lindex $new_node_list 1]
    set weight [lindex $new_node_list 2] ; set label [lindex $new_node_list 3]
    set dash [lindex $new_node_list 4] ; set radius [lindex $new_node_list 5]

    # if any of the entries is invalid, give an error message and return
    if { ![regexp -- $igd_applIntPattern $x] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not create node: \n invalid x coordinate\n"
	return    
    } elseif { ![regexp -- $igd_applIntPattern $y] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not create node: \n invalid y coordinate\n"
	return    
    }
    if { ![regexp -- $igd_applDashPattern $dash] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not create node: \n invalid dash pattern\n"
	return    
    }
    if { ![regexp -- $igd_applIntPattern $radius] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not create node: \n invalid radius\n"
	return    
    }
    
    # display the node and its weight (if any)
    Igd_MakeNode $window $node $x $y $label $dash $radius
    if { ![regexp -- $igd_applSpacesPattern $weight] } {
	Igd_MakeNodeWeight $window $node $weight
    }
    
    # if the same coordinates were used as in the register, update the 
    # register to contain the label and the node id of the new node
    if { $x == $old_x && $y == $old_y } {
	set igd_windowRegisters(1,label,$window) $label
	set igd_windowRegisters(1,node,$window) $node
	Igd_update_registers $toplevel_name
    }
}

#############################################################################
# Modify a given node.
#############################################################################
proc Igd_modify_node { toplevel_name } {
    
    global igd_windowFromToplevel igd_windowRegisters igd_windowDesc \
	    igd_applIntPattern igd_applDashPattern igd_applSpacesPattern \
	    igd_applIntOrEmptyPattern \
	    igd_nodeCoord igd_nodeDesc igd_nodeWidgetID

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that for modification
    set l [Igd_GetNodeFromRegister $window 1]

    if { [set node $igd_windowRegisters(1,node,$window)] != "" } {
	set tmp "$window,$node"
	set old_x $igd_nodeCoord(x,$tmp) ; set old_y $igd_nodeCoord(y,$tmp)
	if { [info exists igd_nodeWidgetID(weight,$tmp)] } {
	    set old_weight $igd_nodeDesc(weight,$tmp)
	} else {
	    set old_weight ""
	}
	set old_label $igd_nodeDesc(label,$tmp)
	set old_dash $igd_nodeDesc(dash,$tmp)
	set old_radius $igd_nodeDesc(radius,$tmp)
    } else {
	set old_x "" ; set old_y "" ; set old_weight ""
	set old_label "" ; set old_dash $igd_windowDesc(node_dash,$window) 
	set old_radius $igd_windowDesc(node_radius,$window)
    }

    set entry_length 20
    set arg0 [list entry "node to be modified: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by: " [lindex $l 0]  \
	    [list "label" "node id"]]
    set arg2 [list entry "x coord (node is deleted if none): " \
	    $old_x $entry_length]
    set arg3 [list entry "y coord (node is deleted if none): " \
	    $old_y $entry_length]
    set arg4 [list entry "weight (optional): " $old_weight $entry_length]
    set arg5 [list entry "label (optional): " $old_label $entry_length]
    set arg6 [list entry "dash pattern (optional): " $old_dash $entry_length]
    set arg7 [list entry "radius (default if none): " \
	    $old_radius $entry_length]

    set node_list [Igd_dialog_box2 $toplevel_name.ask "Modify node" \
	    $arg0 $arg1 $arg2 $arg3 $arg4 $arg5 $arg6 $arg7]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set tomodify [lindex $node_list 0]
    set tomodify_given_with_id [lindex $node_list 1]

    if { [set node [Igd_IdentifyNode $window $tomodify \
	    $tomodify_given_with_id 1]] == "" } {
	return
    }

    # now we can interpret the list returned
    set x [lindex $node_list 2] ; set y [lindex $node_list 3]
    set weight [lindex $node_list 4] ; set label [lindex $node_list 5]
    set dash [lindex $node_list 6] ; set radius [lindex $node_list 7]
    
    # delete node if any of the coordinates is deleted
    if { [regexp -- $igd_applSpacesPattern $x] || \
	    [regexp -- $igd_applSpacesPattern $y] } {
	Igd_DeleteNode $window $node
	set igd_windowRegisters(1,node,$window) ""
	set igd_windowRegisters(1,label,$window) ""
	Igd_update_registers $toplevel_name
	return
    }
    if { ![regexp -- $igd_applIntPattern $x] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not modify node: \n invalid x coordinate\n"
	return    
    } elseif { ![regexp -- $igd_applIntPattern $y] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not modify node: \n invalid y coordinate\n"
	return    
    }
    if { ![regexp -- $igd_applDashPattern $dash] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not modify node: \n invalid dash pattern\n"
	return    
    }
    if { ![regexp -- $igd_applIntOrEmptyPattern $radius] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not modify node: \n invalid radius\n"
	return    
    }
    if { [regexp -- $igd_applSpacesPattern $radius] } {
	set radius $igd_windowDesc(node_radius,$window)
    }
    
    # coordinates have been changed: move the node
    if { $x != $igd_nodeCoord(x,$window,$node) \
	    || $y != $igd_nodeCoord(y,$window,$node) } {
	Igd_MoveNode $window $node [expr $x - $igd_nodeCoord(x,$window,$node)]\
		[expr $y - $igd_nodeCoord(y,$window,$node)]
	set igd_windowRegisters(1,x,$window) $x
	set igd_windowRegisters(1,y,$window) $y
	Igd_update_registers $toplevel_name
    }

    # weights
    if { [info exists igd_nodeDesc(weight,$window,$node)] } {
	if { ![regexp -- $igd_applSpacesPattern $weight] } {
	    if { $weight != $igd_nodeDesc(weight,$window,$node) } { 
		Igd_ChangeOneNodeWeight $window $node $weight
	    }
	} else { Igd_DeleteNodeWeight $window $node }
    } else {
	if { ![regexp -- $igd_applSpacesPattern $weight] } {
	    Igd_MakeNodeWeight $window $node $weight
	}
    }
    
    # label
    if { $label != $igd_nodeDesc(label,$window,$node) } {
	Igd_ChangeOneNodeLabel $window $node $label
	set igd_windowRegisters(1,label,$window) $label
	Igd_update_registers $toplevel_name
    }

    # dash pattern
    if { $dash != $igd_nodeDesc(dash,$window,$node) } {
	Igd_ChangeOneNodeDash $window $node $dash
    }

    # radius
    if { $radius != $igd_nodeDesc(radius,$window,$node) } {
	Igd_ChangeOneNodeRadius $window $node $radius
    }
}

#############################################################################
# Choose new coordinates for a node. If there is a node in Register 1, 
# it will be proposed for moving. 
#############################################################################

proc Igd_move_node { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_applSpacesPattern \
	    igd_applIntPattern igd_nodeCoord

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that for moving
    set l [Igd_GetNodeFromRegister $window 1]
    
    set entry_length 20
    set arg0 [list entry "Move node: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by " [lindex $l 0] \
	    [list "label" "node id"]]
    set arg2 [list entry "to coordinates x: " "" $entry_length]
    set arg3 [list entry "               y: " "" $entry_length]
    set node_list [Igd_dialog_box2 $toplevel_name.ask "Move node" \
	    $arg0 $arg1 $arg2 $arg3]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set tomove [lindex $node_list 0]
    set tomove_given_with_id [lindex $node_list 1]

    if { [set node \
	  [Igd_IdentifyNode $window $tomove $tomove_given_with_id 1]] == "" } {
	return
    }
    
    # now check that the coordinates given are valid
    set new_x [lindex $node_list 2]
    set new_y [lindex $node_list 3]
    
    # don't move the node if any of the coordinates is left empty
    if { [regexp -- $igd_applSpacesPattern $new_x] || \
	    [regexp -- $igd_applSpacesPattern $new_y] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n       Could not move node: \n \
		one (or more) coordinates were left empty \n"
	return
    }

    # give error message if invalid coordinates
    if { ![regexp -- $igd_applIntPattern $new_x] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not move node: \n invalid x coordinate\n"
	return    
    } elseif { ![regexp -- $igd_applIntPattern $new_y] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not move node: \n invalid y coordinate\n"
	return    
    }

    # now the node can be moved
    set xdist [expr $new_x - $igd_nodeCoord(x,$window,$node)]
    set ydist [expr $new_y - $igd_nodeCoord(y,$window,$node)]
    if { $xdist != 0 || $ydist != 0 } {
	Igd_MoveNode $window $node $xdist $ydist

	# if the node is in any of the registers, modify the position stored 
	# in the register
	if { $igd_windowRegisters(1,node,$window) == $node } {
	    set igd_windowRegisters(1,x,$window) $new_x
	    set igd_windowRegisters(1,y,$window) $new_y
	}
	if { $igd_windowRegisters(2,node,$window) == $node } {
	    set igd_windowRegisters(2,x,$window) $new_x
	    set igd_windowRegisters(2,y,$window) $new_y
	}
	Igd_update_registers $toplevel_name
    }
}

#############################################################################
# Raise a node above all the other nodes on the display (i.e., the node will 
# NOT be covered by other nodes). If there is a node in Register 1, it will 
# be proposed to be raised.
#############################################################################

proc Igd_raise_node { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_applSpacesPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that to be raised
    set l [Igd_GetNodeFromRegister $window 1]

    set entry_length 20
    set arg0 [list entry "node to be raised: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by " [lindex $l 0] \
	    [list "label" "node id"]]
    set node_list [Igd_dialog_box2 $toplevel_name.ask "Raise node" $arg0 $arg1]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set toberaised [lindex $node_list 0]
    set toberaised_given_with_id [lindex $node_list 1]

    if { [set node [Igd_IdentifyNode $window $toberaised \
	    $toberaised_given_with_id 1]] == "" } {
	return
    }

    # now the node can be raised
    Igd_RaiseNode $window $node
}

#############################################################################
# Lower a node below all the other nodes on the display (i.e., the node will 
# NOT cover other nodes). If there is a node in Register 1, it will be 
# proposed to be lowered.
#############################################################################

proc Igd_lower_node { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_applSpacesPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that to be lowered
    set l [Igd_GetNodeFromRegister $window 1]

    set entry_length 20
    set arg0 [list entry "node to be lowered: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by " [lindex $l 0] \
	    [list "label" "node id"]]
    set node_list [Igd_dialog_box2 $toplevel_name.ask "Lower node" $arg0 $arg1]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set tobelowered [lindex $node_list 0]
    set tobelowered_given_with_id [lindex $node_list 1]

    if { [set node [Igd_IdentifyNode $window $tobelowered \
	    $tobelowered_given_with_id 1]] == "" } {
	return
    }

    # now the node can be lowered
    Igd_LowerNode $window $node
}

#############################################################################
# Display information about a node, e.g., its coordinates, weight,
# label, outline, radius; its degree and the edges adjacent to it.
# If there is a node in Register 1, it will be proposed.
#############################################################################

proc Igd_node_info { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_applSpacesPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that to give info about
    set l [Igd_GetNodeFromRegister $window 1]
    
    set entry_length 20
    set arg0 [list entry "info about node: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by "  [lindex $l 0] \
	    [list "label" "node id"]]
    set node_list [Igd_dialog_box2 $toplevel_name.ask "Node info" $arg0 $arg1]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set todisp [lindex $node_list 0]
    set todisp_given_with_id [lindex $node_list 1]

    if { [set node \
	    [Igd_IdentifyNode $window $todisp $todisp_given_with_id 1]] \
	    == "" } {
	return
    }

    # now display node information
    Igd_InfoNode $window $node 
}

#############################################################################
# Delete a node. All the edges adjacent to the node will be deleted
# also. If there is a node in Register 1, it will be proposed for deletion.
#############################################################################

proc Igd_delete_node { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_applSpacesPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there is a node in the register, propose that for deletion
    set l [Igd_GetNodeFromRegister $window 1]

    set entry_length 20
    set arg0 [list entry "node to be deleted: " [lindex $l 1] $entry_length]
    set arg1 [list radio "    node is given by " [lindex $l 0] \
	    [list "label" "node id"]]
    set node_list [Igd_dialog_box2 $toplevel_name.ask \
	    "Delete node" $arg0 $arg1]

    # if cancel was pressed, simply return from this function
    if { $node_list == "CANCEL" } {
	return
    }

    set todelete [lindex $node_list 0]
    set todelete_given_with_id [lindex $node_list 1]

    if { [set node \
	    [Igd_IdentifyNode $window $todelete $todelete_given_with_id 1]]\
	    == "" } {
	return
    }

    # now delete the node
    Igd_DeleteNode $window $node

    # if the node is in any of the registers, delete it from there
    if { $igd_windowRegisters(1,node,$window) == $node } {
	set igd_windowRegisters(1,node,$window) ""
	set igd_windowRegisters(1,label,$window) ""
    }
    if { $igd_windowRegisters(2,node,$window) == $node } {
	set igd_windowRegisters(2,node,$window) ""
	set igd_windowRegisters(2,label,$window) ""
    }
    Igd_update_registers $toplevel_name
    
}


#############################################################################
# Display information about the node.
#############################################################################

proc Igd_InfoNode { window node } {

    global igd_windowToplevel igd_nodeCoord igd_nodeDesc igd_nodeEdges \
	    igd_edgeEnds 
    
    set tmp "$window,$node"

    set text ""
    append text [format "Coordinates: (%d,%d)\n" $igd_nodeCoord(x,$tmp) \
	    $igd_nodeCoord(y,$tmp)]
    append text [format "Internal ID: %s \n" $node]
    append text [format "Label: %s \n" $igd_nodeDesc(label,$tmp)]
    append text [format "Dash pattern: %s \n" $igd_nodeDesc(dash,$tmp)]
    append text [format "Radius: %d \n" $igd_nodeDesc(radius,$tmp)]
    if { [info exists igd_nodeDesc(weight,$tmp)] } {
	append text [format "Weight: %s \n" $igd_nodeDesc(weight,$tmp)]
    }
    set degree [expr [llength $igd_nodeEdges(out,$tmp)] + \
	    [llength $igd_nodeEdges(in,$tmp)] ]
    append text [format "Degree of this node: %d\n" $degree]
    if { $degree } {
	append text [format "Edges adjacent to this node: \n"]
	foreach edge $igd_nodeEdges(out,$tmp) {
	    append text [format "\t (%s,%s) \n" $igd_nodeDesc(label,$tmp) \
		    $igd_nodeDesc(label,$window,$igd_edgeEnds(head,$window,$edge))]
	}
	foreach edge $igd_nodeEdges(in,$tmp) {
	    append text [format "\t (%s,%s) \n" \
		    $igd_nodeDesc(label,$window,$igd_edgeEnds(tail,$window,$edge)) \
		    $igd_nodeDesc(label,$tmp)]
	}
    }

    Igd_message_box $igd_windowToplevel($window).infobox \
	    "Node info" 500 0 $text
}

