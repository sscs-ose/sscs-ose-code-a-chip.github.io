#############################################################################
# Pops up a dialog window to get the description of a new edge
# (endpoints, weight, outline) from the user. If there are nodes in the
# registers, they will be proposed as endpoints for the new edge. The
# deafult dash pattern is displayed in the cooresponding entry. The edge
# will not be displayed if invalid endpoints are given. 
#############################################################################

proc Igd_add_edge { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_windowDesc \
	    igd_windowEdgeNum igd_applSpacePattern igd_applDashPattern

    set window $igd_windowFromToplevel($toplevel_name)

    # if there are nodes in the registers, propose the new edge between those
    set t [Igd_GetNodeFromRegister $window 1]
    set h [Igd_GetNodeFromRegister $window 2]
    
    set entry_length 20
    set arg0 [list entry "one endpoint of new edge: " \
	    [lindex $t 1] $entry_length]
    set arg1 [list radio "    node is given by " [lindex $t 0] \
	    [list "label" "node id"]]
    set arg2 [list entry "other endpoint: " [lindex $h 1] $entry_length]
    set arg3 [list radio "    node is given by " [lindex $h 0] \
	    [list "label" "node id"]]
    set arg4 [list entry "weight (optional): " "" $entry_length]
    set arg5 [list entry "dash pattern (optional): " \
	    $igd_windowDesc(edge_dash,$window) $entry_length]
    set edge_list [Igd_dialog_box2 $toplevel_name.ask "Add edge" \
	    $arg0 $arg1 $arg2 $arg3 $arg4 $arg5]

    # if cancel was pressed, simply return from this function
    if { $edge_list == "CANCEL" } {
	return
    }
    
    set tail [lindex $edge_list 0]
    set tail_given_with_id [lindex $edge_list 1]
    set head [lindex $edge_list 2]
    set head_given_with_id [lindex $edge_list 3]

    if { [set tail_node \
	    [Igd_IdentifyNode $window $tail $tail_given_with_id 1]]  == "" || \
	    [set head_node \
	    [Igd_IdentifyNode $window $head $head_given_with_id 1]]  == "" } {
	return
    }

    set weight [lindex $edge_list 4]
    set dash [lindex $edge_list 5]

    # check whether the dash pattern is valid
    if { [regexp -- $igd_applDashPattern $dash] == 0 } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Could not create edge: \n invalid dash pattern\n"
	return        
    }

    # create the edge
    set edge [expr $igd_windowEdgeNum($window) + 1]
    Igd_MakeEdge $window $edge $tail_node $head_node $dash
    if { $weight != "" } {
	Igd_MakeEdgeWeight $window $edge $weight
    }
}

#############################################################################
# Pops up a dialog window so that the user can enter modifications to an
# edge (modify its weight and outline). If there are nodes in the
# registers, they will be proposed as the endpoints of the edge (if edge
# exists between them). If more than one edge exists between two nodes,
# the lastly added will be considered. 
#############################################################################

proc Igd_modify_edge { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters igd_windowDesc \
	    igd_edgeDesc igd_applSpacesPattern igd_edgeWidgetID igd_edgeDesc

    set window $igd_windowFromToplevel($toplevel_name)

    # if there are nodes in the registers, check whether there are edges
    # between them. If yes, fill the entries with these nodes and the 
    # data of the edge added lastly between them.

    if { [set n1 $igd_windowRegisters(1,node,$window)] != "" && \
	    [set n2 $igd_windowRegisters(2,node,$window)] != "" && \
	    [set candidate_list [Igd_ExistsEdgeBetweenNodes $window $n1 $n2]] \
	    != "" } {
	set t [Igd_GetNodeFromRegister $window 1]
	set h [Igd_GetNodeFromRegister $window 2]
	set t_given_with_id [lindex $t 0]
	set t_text [lindex $t 1]
	set h_given_with_id [lindex $h 0]
	set h_text [lindex $h 1]
	set old_edge [lindex $candidate_list end]
	set old_dash $igd_edgeDesc(dash,$window,$old_edge)
	if { [info exists igd_edgeWidgetID(weight,$window,$old_edge)] } {
	    set old_weight $igd_edgeDesc(weight,$window,$old_edge)
	} else {
	    set old_weight ""
	}
    } else {
	set t_given_with_id 0 ; set t_text "" ; set h_given_with_id 0
	set h_text "" ; set old_dash $igd_windowDesc(edge_dash,$window)
	set old_weight "" ; set old_edge ""
    }

    set entry_length 20
    set arg0 [list entry "one endpoint of edge to be modified: " \
	    $t_text $entry_length]
    set arg1 [list radio "    node is given by " $t_given_with_id \
	    [list "label" "node id"]]
    set arg2 [list entry "other endpoint: " $h_text $entry_length]
    set arg3 [list radio "    node is given by " $h_given_with_id \
	    [list "label" "node id"]]
    set arg4 [list entry "weight (optional): " $old_weight $entry_length]
    set arg5 [list entry "dash pattern (optional): " \
	    $old_dash $entry_length]
    set edge_list [Igd_dialog_box2 $toplevel_name.ask "Modify edge" \
	    $arg0 $arg1 $arg2 $arg3 $arg4 $arg5]

    # if cancel was pressed, simply return from this function
    if { $edge_list == "CANCEL" } {
	return
    }
    
    set tail [lindex $edge_list 0]
    set tail_given_with_id [lindex $edge_list 1]
    set head [lindex $edge_list 2]
    set head_given_with_id [lindex $edge_list 3]

    if { [set tail_node \
	    [Igd_IdentifyNode $window $tail $tail_given_with_id 1]] == "" || \
	    [set head_node \
	    [Igd_IdentifyNode $window $head $head_given_with_id 1]] == "" } {
	return
    }

    if { [set candidate_list \
	    [Igd_ExistsEdgeBetweenNodes $window $tail_node $head_node]] !=""} {
	set edge [lindex $candidate_list end]
	set weight [lindex $edge_list 4]
	set dash [lindex $edge_list 5]

	# weights
	if { [info exists igd_edgeDesc(weight,$window,$edge)] } {
	    if { ![regexp -- $igd_applSpacesPattern $weight] } {
		if { $weight != $igd_edgeDesc(weight,$window,$edge) } {
		    # weight exists and new weight is different -- change
		    Igd_ChangeOneEdgeWeight $window $edge $weight
		}
	    } else {
		# weight exists and new weight is all spaces -- delete weight
		Igd_DeleteEdgeWeight $window $edge 
	    }
	} else {
	    if { ![regexp -- $igd_applSpacesPattern $weight] } {
		# weight didn't exist before 
		Igd_MakeEdgeWeight $window $edge $weight
	    }
	}

	# dash
	if { $dash != $igd_edgeDesc(dash,$window,$edge) \
		&& [Igd_ValidDashPattern $window $dash] } {
	    Igd_ChangeOneEdgeDash $window $edge $dash
	}
	
	Igd_print_msg $toplevel_name "Modified edge"
    } else {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n No edge exists between the two nodes \n"
    }	

}

#############################################################################
# Pops up a dialog window to get a pair of nodes from the user and then
# calls Igd_InfoEdge} to display information about ALL the
# edges between those two nodes. If there are nodes in the registers,
# they will be proposed.
#############################################################################

proc Igd_edge_info { toplevel_name } {
    
    global igd_windowFromToplevel igd_windowRegisters
    
    set window $igd_windowFromToplevel($toplevel_name)
    
    # if both registers have nodes in them, fill the entries with those
    if { [set n1 $igd_windowRegisters(1,node,$window)] != "" && \
	    [set n2 $igd_windowRegisters(2,node,$window)] != "" } {
	set t [Igd_GetNodeFromRegister $window 1]
	set h [Igd_GetNodeFromRegister $window 2]
	set t_given_with_id [lindex $t 0]
	set t_text [lindex $t 1]
	set h_given_with_id [lindex $h 0]
	set h_text [lindex $h 1]
    } else {
	set t_given_with_id 0 ; set t_text ""
	set h_given_with_id 0 ; set h_text ""
    }

    set entry_length 20
    set arg0 [list entry "info about edges between: " \
	    $t_text $entry_length]
    set arg1 [list radio "     node is given by " $t_given_with_id \
	    [list "label" "node id"]]
    set arg2 [list entry "                     and: " \
	    $h_text $entry_length]
    set arg3 [list radio "     node is given by " $h_given_with_id \
	    [list "label" "node id"]]
    set edge_list [Igd_dialog_box2 $toplevel_name.ask "Edge info" \
	    $arg0 $arg1 $arg2 $arg3]

    # if cancel was pressed, simply return from this function
    if { $edge_list == "CANCEL" } {
	return
    }

    set tail [lindex $edge_list 0]
    set tail_given_with_id [lindex $edge_list 1]
    set head [lindex $edge_list 2]
    set head_given_with_id [lindex $edge_list 3]

    if { [set tail_node \
	    [Igd_IdentifyNode $window $tail $tail_given_with_id 1]] == "" || \
	    [set head_node \
	    [Igd_IdentifyNode $window $head $head_given_with_id 1]] == "" } {
	return
    }

    Igd_InfoEdge $window $tail_node $head_node
}

#############################################################################
# Pops up a dislog box to get an edge from the user and then calls 
# Igd_DeleteEdge to delete it. An edge is specified with its
# endpoints, if there are more than one edges between a pair of nodes,
# the lastly added one is considered. 
# (This can be easily modified by specifying something else instead of the
# 'end' in the last if statement.)
#############################################################################

proc Igd_delete_edge { toplevel_name } {

    global igd_windowFromToplevel igd_windowRegisters 

    set window $igd_windowFromToplevel($toplevel_name)

    # if there are nodes in the registers, check whether there are edges
    # between them. If yes, fill the entries with these two nodes.
    if { [set n1 $igd_windowRegisters(1,node,$window)] != "" && \
	    [set n2 $igd_windowRegisters(2,node,$window)] != "" && \
	    [Igd_ExistsEdgeBetweenNodes $window $n1 $n2] != "" } {
	set t [Igd_GetNodeFromRegister $window 1]
	set h [Igd_GetNodeFromRegister $window 2]
	set t_given_with_id [lindex $t 0]
	set t_text [lindex $t 1]
	set h_given_with_id [lindex $h 0]
	set h_text [lindex $h 1]
    } else {
	set t_given_with_id 0 ; set t_text ""
	set h_given_with_id 0 ; set h_text ""
    }

    set entry_length 20
    set arg0 [list entry "one endpoint of edge to be deleted: " \
	    $t_text $entry_length]
    set arg1 [list radio "     node is given by " $t_given_with_id \
	    [list "label" "node id"]]
    set arg2 [list entry "                    other endpoint: " \
	    $h_text $entry_length]
    set arg3 [list radio "     node is given by " $h_given_with_id \
	    [list "label" "node id"]]
    set edge_list [Igd_dialog_box2 $toplevel_name.ask "Delete edge" \
	    $arg0 $arg1 $arg2 $arg3]

    # if cancel was pressed, simply return from this function
    if { $edge_list == "CANCEL" } {
	return
    }

    set tail [lindex $edge_list 0]
    set tail_given_with_id [lindex $edge_list 1]
    set head [lindex $edge_list 2]
    set head_given_with_id [lindex $edge_list 3]

    if { [set tail_node \
	    [Igd_IdentifyNode $window $tail $tail_given_with_id 1]] == "" || \
	    [set head_node \
	    [Igd_IdentifyNode $window $head $head_given_with_id 1]] == "" } {
	return
    }

    if { [set edge [lindex [Igd_ExistsEdgeBetweenNodes $window $tail_node \
	$head_node] end]] \
	    != "" } {
	Igd_DeleteEdge $window $edge
	Igd_print_msg $toplevel_name "Edge between nodes $tail and $head with\
		edge id $edge has been deleted"
    } else {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n No edge exists between the two nodes \n"
    }
}

#############################################################################
# Display information about ALL edges between the two specified endpoints.
#############################################################################

proc Igd_InfoEdge { window tail head } {

    global igd_windowToplevel igd_edgeDesc igd_nodeDesc

    set candidate_list [Igd_ExistsEdgeBetweenNodes $window $tail $head]
    set text ""
    append text [format "Endpoints:\n\t %s (label)  %s (node id)\n\
	         \t %s (label)  %s (node id)\n" \
		 $igd_nodeDesc(label,$window,$tail)\
		 $tail $igd_nodeDesc(label,$window,$head) $head]
    
    if { $candidate_list != "" } {
	# gather all the information about the edges 
	append text [format "Edges between the two nodes:\n"]
	foreach edge $candidate_list {
	    append text [format "\t edge id: %s   dash pattern: %s" \
		    $edge $igd_edgeDesc(dash,$window,$edge)]
	    if { [info exists igd_edgeDesc(weight,$window,$edge)] } {
		append text [format "   weight: %s" \
			$igd_edgeDesc(weight,$window,$edge)]
	    }
	    append text [format "\n"]
	}
    } else {
	# there are no edges between the nodes
	append text [format "\n There are no edges between the two nodes\n"]
    }
    
    Igd_message_box $igd_windowToplevel($window).infobox \
	    "Edge info" 500 0 $text
}
