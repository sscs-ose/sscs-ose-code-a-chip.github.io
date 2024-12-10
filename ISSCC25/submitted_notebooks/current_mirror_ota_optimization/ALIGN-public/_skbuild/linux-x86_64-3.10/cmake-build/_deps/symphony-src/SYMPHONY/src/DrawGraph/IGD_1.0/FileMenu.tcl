#############################################################################
#  Pops up a dialog window to get the input file name from the user, then 
#  calls Igd_LoadGraph {window fname} to do the dirty work. If the file 
#  fname doesn't exist, Igd_LoadGraph will give an error message in the 
#  message window and nothing happens. For input file format see the
#  comments at Igd_LoadGraph.
#############################################################################

proc Igd_load_from_file { toplevel_name } {
    
    global igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name)

    set entry_length 30
    set arg0 [list "Load graph from file: " "~/vrp_pics/" $entry_length]
    set fname [join [Igd_dialog_box $toplevel_name.ask \
	"Load graph from file" $arg0]]
    if { [string length $fname] && ($fname != "CANCEL")} {
	if { [Igd_LoadGraph $window $fname] } {
	    Igd_print_msg $toplevel_name "Loaded graph from file $fname"
	}
    } else {
	Igd_print_msg $toplevel_name "No graph has been loaded"
    }
}

#############################################################################
#  Pops up a dialog window to get the output file name from the user, then 
#  calls Igd_SaveGraph {window fname} to save the graph on window's canvas.
#  If the file already exists, Igd_SaveGraph will overwrite it.
#############################################################################

proc Igd_save_to_file { toplevel_name } {

    global igd_windowFromToplevel
    
    set window $igd_windowFromToplevel($toplevel_name)

    set entry_length 30
    set arg0 [list "Save graph to file: " "~/vrp_pics/" $entry_length]
    set fname [join [Igd_dialog_box $toplevel_name.ask \
	"Save graph to file" $arg0]]
    if { [string length $fname] && ($fname != "CANCEL")} {
	if { [Igd_SaveGraph $window $fname] } {
	    Igd_print_msg $toplevel_name "Saved graph into file $fname"
	}
    } else {
	Igd_print_msg $toplevel_name "Graph hasn't been saved"
    }
}

#############################################################################
#  Pops up a dialog window to get the output file name from the user, then
#  calls Igd_SavePs {window fname} to save the postscript version of the graph 
#  on window's canvas. If file already exists, Igd_SavePs will overwrite it.
#############################################################################

proc Igd_save_postscript_to_file { toplevel_name } {
    
    global igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name)

    set entry_length 30
    set arg0 [list "Save PostScript to file: " "~/vrp_pics/" $entry_length]
    set fname [join [Igd_dialog_box $toplevel_name.ask \
	"Save PostScript" $arg0]]
    if {[string length $fname] && ($fname != "CANCEL")} {
	if { [Igd_SavePs $window $fname] } {
	    Igd_print_msg $toplevel_name "PostScript saved into file $fname"
	}
    } else {
	Igd_print_msg $toplevel_name "PostScript hasn't been saved"
    }
}

#############################################################################
# Quit the whole application.
#############################################################################

proc Igd_QuitAll {} {

    global igd_applWindows igd_applWindowCount igd_applWindowNum \
	    igd_applDefaults igd_applIntPattern igd_applIntOrEmptyPattern \
	    igd_applDashPattern igd_applSpacesPattern igd_applDescList \
	    igd_applCheckFonts

    # get rid of all the windows
    foreach window $igd_applWindows {
	Igd_QuitWindow $window
    }

    # unset all the variables
    foreach option $igd_applDescList {
	unset igd_applDefaults($option) 
    }

    unset igd_applWindows igd_applWindowCount igd_applWindowNum \
	    igd_applIntPattern igd_applIntOrEmptyPattern igd_applDashPattern \
	    igd_applSpacesPattern igd_applDescList igd_applCheckFonts

    # now exit from the application
    exit
}

#############################################################################
#  Read the graph from file fname. The input file format is the following:
#      c Empty lines or lines starting with a 'c' will be skipped.
#    First list the window properties, like this:
#      w node_dash {2 2}    
#    Then give the number of nodes and edges
#      p nodenum edgenum    -- number of nodes and edges
#    List the descriptions of nodes. The nodes are going to be displayed in 
#    this order.
#      n node_id x y key weight label dash radius  
#        node_id:  identifier of the node. should be unique.
#        x, y: coordinates of the node.
#        key: indicates (as a binary number) which of the following  
#             data is given: weight, label, dash pattern, radius.
#             e.g., if key = 1101_2 = 11 = 8+2+1 then the weight, 
#             dash pattern, and radius are listed after the key 
#             (in this order), but not the label.
#    List the descriptions of edges. The edges are going to be displayed in
#    this order.
#      a edge_id tail head key weight dash
#        edge_id: identifier of the edge.
#        tail, head: node identifiers of the endpoints of the edge.
#        key: indicates (as a binary number) which of the following
#             data is given: weight, dash patter. To be consistent with
#             notation at nodes, weight adds 8, dash pattern adds 2 to key.
#
#    Note : values containing spaces must be enclosed in brackets {}.
# 
#  The function first opens the file fname, creates a dummy window to
#  load the graph into that. If the end of the file is reached without
#  any problems then the window is erased and the dummy graph is copied 
#  onto the window.
#  The file is read line by line. Empty lines or lines starting with a 'c'
#  are skipped. First the window description and the number of nodes/edges
#  have to be given, then description of nodes, then description of edges.
#  The id, coordinates, and the key are required for a node. If weight is
#  not given, no weight will be displayed; if no label is given, the id
#  of the node is going to be displayed as its label; if no dash pattern
#  or radius is given, default values will be used.
#  Similarly for the edges, the id, endpoints and key are required; no
#  weight is displayed if none given; and default value is used if dash
#  pattern is not given.
#
#  The function returns 1 if successful, 0 if not.
#############################################################################

proc Igd_LoadGraph { window fname } {

    global igd_applDescList igd_applIntPattern igd_windowToplevel \
	    igd_windowDesc igd_windowTitle igd_windowNodes igd_windowEdges \
	    igd_nodeCoord igd_nodeDesc igd_edgeEnds igd_edgeDesc

    set toplevel_name $igd_windowToplevel($window)
    
    # open the file for reading only. If file doesn't exist, give error
    # message
    if { [catch {open $fname r} f] } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n ERROR while trying to open the file $fname for reading:\n \
		\n $f\n"
	return 0
    }

    # everything will be loaded into a temporary graph, so that if there
    # are problems during loading, the original setup and the graph in
    # the window are not destroyed.
    set tmp_win "__tmp__"

    # copy the application defaults to this window
    Igd_CopyApplDefaultToWindow $tmp_win

    # read in the window description, and number of nodes and edges.
    
    # read in a line first
    if { [catch {gets $f line} r] } {
	Igd_load_error $window $fname $r
	return 0
    }

    while { ![eof $f] } {
	set key [lindex $line 0]
	
	switch -exact -- $key {
	    c {
	    }
	    "" {
	    }
	    w {
		if { [llength $line] != 3 } {
		    Igd_load_incorrect_num $window $fname $line
		    return 0
		}
		set option [lindex $line 1]
		if { $option == "title" } {
		    set igd_windowTitle($tmp_win) [lindex $line 2]
		} else {
		    if { [lsearch $igd_applDescList $option] >= 0 } {
			set igd_windowDesc($option,$tmp_win) [lindex $line 2]
		    }
		}
	    }
	    p {
		if { [llength $line] != 3 } {
		    Igd_load_incorrect_num $window $fname $line
		    return 0
		}
		set win_tmp_nodenum [lindex $line 1]
		set win_tmp_edgenum [lindex $line 2]
		# if nodenum and edgenum are not integers, return
		if { ![regexp -- $igd_applIntPattern $win_tmp_nodenum] || \
			![regexp -- $igd_applIntPattern $win_tmp_edgenum] } {
		    Igd_message_box $toplevel_name.mbox error 500 1 \
			    "\n Number of nodes and edges have to be integers.\
			    \n Loading graph aborted. \n "
		    return 0
		} 
		# if nodenum 0 but edgenum is nonzero, return
		if { $win_tmp_nodenum == 0 && $win_tmp_edgenum != 0 } {
		    Igd_message_box $toplevel_name.mbox error 500 1 \
			    "\n Number of nodes is zero but number of edges\n\
			     is nozero. Loading graph aborted. \n"
		    return 0
		}
	    }		
	    n {
		break
	    }
	    a {
		break
	    }
	    default {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Expected a line starting with a c or w\n \
			but got $key. Loading graph aborted.\n"
		return 0
	    }
	}
	# read in a line
	if { [catch {gets $f line} r] } {
	    Igd_load_error $window $fname $r
	    return 0
	}
    }

    # if p nodenum edgenum is missing, give error message
    if { ![info exists win_tmp_nodenum] || ![info exists win_tmp_edgenum] } {
	Igd_load_error $window $fname "Did not get a line with the number\
		of nodes and edges. \n"
	return 0
    }

    # now read in the description of nodes. the first node info is already 
    # in line.
    set node_count 0
    set igd_windowNodes($tmp_win) {}
    while { ![eof $f] } {
	set key [lindex $line 0]

	switch -exact -- $key {
	    c {
	    }
	    "" {
	    }
	    n { 
		if { [Igd_read_node $window $fname $tmp_win $line] } {
		    incr node_count
		} else {
		    return 0
		}
	    }
	    a {
		break
	    }
	    default {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Expected a line starting with a c or n\n \
			but got $key. Loading graph aborted.\n "
		return 0
	    }
	}

	# read in a line 
	if { [catch {gets $f line} r] } {
	    Igd_load_error $window $fname $r
	    return 0
	}
    }

    if { $node_count != $win_tmp_nodenum } {
	Igd_message_box $toplevel_name.mbox warning 500 1 \
		"\n WARNING: Number of nodes was given incorrectly\n"
    }

    # now read in the description of edges. the first edge is already in
    # line
    set edge_count 0
    set igd_windowEdges($tmp_win) {}
    while { ![eof $f] } {
	set key [lindex $line 0]

	switch -exact -- $key {
	    c {
	    }
	    "" {
	    }
	    a { 
		if { [Igd_read_edge $window $fname $tmp_win $line] } {
		    incr edge_count
		} else {
		    return 0
		}
	    }
	    default {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Expected a line starting with a c or a\n \
			but got $key. Loading graph aborted.\n "
		return 0
	    }
	}
	# read in a line 
	if { [catch {gets $f line} r] } {
	    Igd_load_error $window $fname $r
	    return 0
	}
    }

    if { $edge_count != $win_tmp_edgenum } {
	Igd_message_box $toplevel_name.mbox warning 500 1 \
		"\n WARNING: Number of edges was given incorrectly\n"
    }

    # now that the graph has been read in correctly, display it.

    # first erase the window
    Igd_EraseWindow $window

    # set the title of the window
    Igd_RenameWindow $window $igd_windowTitle($tmp_win)

    # copy window descriptions (and have their effect at once)
    Igd_SetAndExecuteWindowDesc $window \
	    $igd_windowDesc(canvas_width,$tmp_win)\
	    $igd_windowDesc(canvas_height,$tmp_win) \
	    $igd_windowDesc(viewable_width,$tmp_win) \
	    $igd_windowDesc(viewable_height,$tmp_win) \
	    $igd_windowDesc(disp_nodelabels,$tmp_win) \
	    $igd_windowDesc(disp_nodeweights,$tmp_win) \
	    $igd_windowDesc(disp_edgeweights,$tmp_win) \
	    $igd_windowDesc(node_dash,$tmp_win) \
	    $igd_windowDesc(edge_dash,$tmp_win) \
	    $igd_windowDesc(node_radius,$tmp_win) \
	    $igd_windowDesc(interactive_mode,$tmp_win) \
	    $igd_windowDesc(mouse_tracking,$tmp_win) \
	    $igd_windowDesc(scale_factor,$tmp_win) \
	    $igd_windowDesc(nodelabel_font,$tmp_win) \
	    $igd_windowDesc(nodeweight_font,$tmp_win) \
	    $igd_windowDesc(edgeweight_font,$tmp_win) 

    # display the nodes
    foreach node $igd_windowNodes($tmp_win) {
	set tmp "$tmp_win,$node"
	Igd_MakeNode $window $node \
		[expr int($igd_nodeCoord(x,$tmp) * $igd_windowDesc(scale_factor,$window)) + 1] \
		[expr int($igd_nodeCoord(y,$tmp) * $igd_windowDesc(scale_factor,$window)) + 1] \
		$igd_nodeDesc(label,$tmp) $igd_nodeDesc(dash,$tmp) \
		$igd_nodeDesc(radius,$tmp)
	if { [info exists igd_nodeDesc(weight,$tmp)] } {
	    Igd_MakeNodeWeight $window $node $igd_nodeDesc(weight,$tmp)
	}
    }
    foreach edge $igd_windowEdges($tmp_win) {
	set tmp "$tmp_win,$edge"
	Igd_MakeEdge $window $edge \
		$igd_edgeEnds(tail,$tmp) $igd_edgeEnds(head,$tmp) \
		$igd_edgeDesc(dash,$tmp)
	if { [info exists igd_edgeDesc(weight,$tmp)] } {
	    Igd_MakeEdgeWeight $window $edge $igd_edgeDesc(weight,$tmp)
	}
    }

    # "erase" and unset the dummy window 
    foreach edge $igd_windowEdges($tmp_win) {
	set tmp "$tmp_win,$edge"
	unset igd_edgeEnds(tail,$tmp) igd_edgeEnds(head,$tmp) \
		igd_edgeDesc(dash,$tmp) 
	if { [info exists igd_edgeDesc(weight,$tmp)] } {
	    unset igd_edgeDesc(weight,$tmp)
	}
    }
    foreach node $igd_windowNodes($tmp_win) {
	set tmp "$tmp_win,$node"
	unset igd_nodeCoord(x,$tmp) igd_nodeCoord(y,$tmp) \
		igd_nodeDesc(radius,$tmp) igd_nodeDesc(dash,$tmp) \
		igd_nodeDesc(label,$tmp)
	if { [info exists igd_nodeDesc(weight,$tmp)] } {
	    unset igd_nodeDesc(weight,$tmp)
	}
    } 
    unset igd_windowTitle($tmp_win) igd_windowNodes($tmp_win) \
	    igd_windowEdges($tmp_win)

    foreach option $igd_applDescList {
	unset igd_windowDesc($option,$tmp_win)
    }
    
    
    return 1

}


#############################################################################
# Interpret the list 'line' as node description. Give an error message if 
# data is invalid.
#############################################################################

proc Igd_read_node { window fname tmp_win line } {

    global igd_applIntPattern igd_applDashPattern igd_applSpacesPattern \
	    igd_windowToplevel igd_windowTitle igd_windowDesc igd_windowNodes \
	    igd_nodeDesc igd_nodeCoord
    
    set toplevel_name $igd_windowToplevel($window)

    set node_id [lindex $line 1]
    if { [lsearch $igd_windowNodes($tmp_win) $node_id] >= 0 } {
	# node id already exists
	Igd_message_box $toplevel_name.mbox warning 500 1 \
		"\n WARNING: node id $node_id already exists, \n \n \
		$line \n \n \
		will not be displayed. (loading graph from file $fname)\n "
    } else {
	if { [llength $line] < 5 || [llength $line] > 9 } {
	    Igd_load_incorrect_num $window $fname $line
	    return 0
	}
	
	set x [lindex $line 2] ; set y [lindex $line 3]
	if { ![regexp -- $igd_applIntPattern $x] } {
	    Igd_message_box $toplevel_name.mbox error 500 1 \
		    "\n Invalid x coordinate in the description of node\n \n \
		    $line \n \n \
		    (loading graph from file $fname)\n"
	    return 0
	}
	if { ![regexp -- $igd_applIntPattern $y] } {
	    Igd_message_box $toplevel_name.mbox error 500 1 \
		    "\n Invalid y coordinate in the description of node\n \n \
		    $line \n \n \
		    (loading graph from file $fname)\n"
	    return 0
	}

	set node_key [lindex $line 4]
	if { ![regexp -- $igd_applIntPattern $node_key] || $node_key > 15 } {
	    Igd_message_box $toplevel_name.mbox error 500 1 \
		    "\n Invalid key in the description of node\n \n \
		    $line \n \n \
		    (loading graph from file $fname)\n"
	    return 0
	}

	set ind 5
	if { [expr $node_key & 0x08] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set w [lindex $line $ind]
	    incr ind
	} else {
	    # no weight is assigned to the node by default, this is just dummy 
	    set w ""
	}
	if { [expr $node_key & 0x04] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set l [lindex $line $ind]
	    incr ind
	} else {
	    # node id is going to be displayed as the label of the node 
	    # if no label is specified
	    set l $node_id
	}
	if { [expr $node_key & 0x02] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set d [lindex $line $ind]
	    if { ![regexp -- $igd_applDashPattern $d] } {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Invalid dash pattern in the description of node\n\
			\n $line \n \n \
			(loading graph from file $fname)\n"
		return 0
	    }
	    incr ind
	} else {
	    # dash will be the default dash if nothing else is specified
	    set d $igd_windowDesc(node_dash,$tmp_win)
	}
	if { [expr $node_key & 0x01] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set r [lindex $line $ind]
	    if { ![regexp -- $igd_applIntPattern $r] } {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Invalid radius in the description of node\n\
			\n $line \n \n \
			(loading graph from file $fname)\n"
		return 0
	    }
	    incr ind
	} else {
	    # default will be used if no radius is given
	    set r $igd_windowDesc(node_radius,$tmp_win)
	}

	# the node is valid: set the data structure:
	lappend igd_windowNodes($tmp_win) $node_id
	set igd_nodeCoord(x,$tmp_win,$node_id) $x
	set igd_nodeCoord(y,$tmp_win,$node_id) $y
	if { ![regexp -- $igd_applSpacesPattern $w] } {
	    set igd_nodeDesc(weight,$tmp_win,$node_id) $w
	}
	set igd_nodeDesc(label,$tmp_win,$node_id) $l
	set igd_nodeDesc(dash,$tmp_win,$node_id) $d
	set igd_nodeDesc(radius,$tmp_win,$node_id) $r

	return 1
    }
}

#############################################################################
# Interpret the list 'line' as edge description. Give an error message if 
# data is invalid.
#############################################################################

proc Igd_read_edge { window fname tmp_win line } { 
    
    global igd_applIntPattern igd_applDashPattern igd_applSpacesPattern \
	    igd_windowToplevel igd_windowTitle igd_windowDesc igd_windowNodes \
	    igd_windowEdges igd_edgeDesc igd_edgeEnds

    set toplevel_name $igd_windowToplevel($window)
    
    set edge_id [lindex $line 1]
    if { [Igd_ExistsEdge $tmp_win $edge_id] } {
	# edge id already exists
	Igd_message_box $toplevel_name.mbox warning 500 1 \
		"\n WARNING: edge id $edge_id already exists, \n \n \
		$line \n \n \
		will not be displayed. (loading graph from file $fname)\n "
    } else {
	if { [llength $line] < 5 || [llength $line] > 7 } {
	    Igd_load_incorrect_num $window $fname $line
	    return 0
	}
	
	set tail [lindex $line 2] ; set head [lindex $line 3]
	if { ![Igd_ExistsNode $tmp_win $tail] || \
		![Igd_ExistsNode $tmp_win $head] } {
	    Igd_message_box $toplevel_name.mbox error 500 1 \
		    "\n One (or both) endpoint(s) of edge \n \n \
		    $line \n \n doesn't exist. Loading graph aborted.\n"
	    return 0
	}
	
	set edge_key [lindex $line 4]
	if { ![regexp -- $igd_applIntPattern $edge_key] || $edge_key > 15 } {
	    Igd_message_box $toplevel_name.mbox error 500 1 \
		    "\n Invalid key in the description of edge\n \n \
		    $line \n \n \
		    (loading graph from file $fname)\n"
	    return 0
	}

	set ind 5
	if { [expr $edge_key & 0x08] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set w [lindex $line $ind]
	    incr ind
	} else {
	    # no weight is assigned to the edge by default, this is just dummy 
	    set w ""
	}
	if { [expr $edge_key & 0x02] > 0 } {
	    if { [llength $line] <= $ind } {
		Igd_load_incorrect_num $window $fname $line
		return 0
	    }
	    set d [lindex $line $ind]
	    if { ![regexp -- $igd_applDashPattern $d] } {
		Igd_message_box $toplevel_name.mbox error 500 1 \
			"\n Invalid dash pattern in the description of edge\n\
			\n $line \n \n \
			(loading graph from file $fname)\n"
		return 0
	    }
	    incr ind
	} else {
	    # dash will be the default dash if nothing else is specified
	    set d $igd_windowDesc(edge_dash,$tmp_win)
	}	
    
	# the edge is valid: set the data structure:
	lappend igd_windowEdges($tmp_win) $edge_id
	set igd_edgeEnds(tail,$tmp_win,$edge_id) $tail
	set igd_edgeEnds(head,$tmp_win,$edge_id) $head
	if { ![regexp -- $igd_applSpacesPattern $w] } {
	    set igd_edgeDesc(weight,$tmp_win,$edge_id) $w
	}
	set igd_edgeDesc(dash,$tmp_win,$edge_id) $d

	return 1
    }
}


#############################################################################
# Error message when loading.
#############################################################################

proc Igd_load_error { window fname text } {

    global igd_windowToplevel
    
    Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
	    "\n ERROR while trying to load from file $fname: \n \n $text \n\
	     Loading graph aborted.\n"
}

#############################################################################
# Error message if the number of entries in a line is incorrect.
#############################################################################

proc Igd_load_incorrect_num { window fname line } {
    
    global igd_windowToplevel

    Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
	    "\n Incorrect number of entries in line\n \n \
	    $line \n \n\
	    while loading from file $fname\n\
	    Loading graph aborted.\n"
}

#############################################################################
# Save the graph on window's canvas into the file fname. If the file fname 
# already exists, it is going to be overwritten. Returns 1 if successfull, 
# 0 if not. Format is the same as at Igd_LoadGraph. 
#############################################################################

proc Igd_SaveGraph { window fname } {

    global igd_applDescList igd_windowToplevel igd_windowTitle igd_windowDesc \
	    igd_windowNodes igd_windowNodeCount igd_windowEdges \
	    igd_applSpacesPattern igd_nodeCoord igd_nodeDesc igd_edgeEnds \
	    igd_edgeDesc

    set toplevel_name $igd_windowToplevel($window)

    # open file for writing only. if file already exists, overwrite.
    # f is going to be the file id if open is successful.
    if { [catch {open $fname w} f] }  {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n ERROR while trying to open the file $fname for writing: \n\
		\n $f\n "
	return 0
    }
    
    puts $f "c The following entries describe the window properties."

    if { [catch {puts $f [list w title $igd_windowTitle($window)]} r] } {
	Igd_save_error $window $fname $r
	return 0
    }
    foreach option $igd_applDescList {
	if { [catch {puts $f [list w $option \
		$igd_windowDesc($option,$window)]} r] } {
	    Igd_save_error $window $fname $r
	    return 0
	}
    }

    puts -nonewline $f "\n"

    puts $f "c The following two numbers are the number of nodes and\
	    edges in the graph"

    set node_count $igd_windowNodeCount($window)
    set edge_count [llength $igd_windowEdges($window)]
    if { [catch {puts $f [list p $node_count $edge_count]} r] } {
	Igd_save_error $window $fname $r
	return 0
    }

    puts -nonewline $f "\n"

    puts $f "c The following entries list the nodes, the nodes are supposed "
    puts $f "c to be displayed exactly in this order. The first number is the "
    puts $f "c node id, the second and third are the node's coordinates."
    puts $f "c The fourth number is a key that indicates (as a binary number)"
    puts $f "c which of the following data is given: weight, label, "
    puts $f "c dash pattern, radius."

    set node_list [Igd_NodeOrderInDisplayList $window]
    foreach node $node_list {
	set tmp "$window,$node"
	set out_list [list n $node \
		[expr int(double($igd_nodeCoord(x,$tmp)) / $igd_windowDesc(scale_factor,$window))] \
		[expr int(double($igd_nodeCoord(y,$tmp)) / $igd_windowDesc(scale_factor,$window))]]
	set key 0
	if { [info exists igd_nodeDesc(weight,$tmp)] } {
	    incr key 8
	    lappend out_list $igd_nodeDesc(weight,$tmp)
	}
	lappend out_list $igd_nodeDesc(label,$tmp) 
	incr key 4
	lappend out_list $igd_nodeDesc(dash,$tmp)
	incr key 2
	lappend out_list $igd_nodeDesc(radius,$tmp)
	incr key 1
	set out_list [linsert $out_list 4 $key]
	if { [catch {puts $f $out_list} r] } {
	    Igd_save_error $window $fname $r
	    return 0
	}
    }
	    
    puts -nonewline $f "\n"

    puts $f "c The following entries list the edges, the edges are supposed"
    puts $f "c to be displayed exactly in this order. The first number is the "
    puts $f "c edge id, the second and third are the node id of its "
    puts $f "c endpoints. The fourth number is a key that indicates (as a"
    puts $f "c binary number) which of the following data is given: weight,"
    puts $f "c dash pattern."

    set edge_list [Igd_EdgeOrderInDisplayList $window]
    foreach edge $edge_list {
	set tmp "$window,$edge"
	set out_list [list a $edge $igd_edgeEnds(tail,$tmp) \
		$igd_edgeEnds(head,$tmp)]
	set key 0
	if { [info exists igd_edgeDesc(weight,$tmp)] } {
	    incr key 8
	    lappend out_list $igd_edgeDesc(weight,$tmp)
	}
	lappend out_list $igd_edgeDesc(dash,$tmp)
	incr key 2
	set out_list [linsert $out_list 4 $key]
	if { [catch {puts $f $out_list} r] } {
	    Igd_save_error $window $fname $r
	    return 0
	}
    }

    # close the file
    if { [catch {close $f} r] } {
	Igd_save_error $window $fname $r
	return 0
    }

    # all went fine
    return 1
}

#############################################################################
# Error message when saving.
#############################################################################

proc Igd_save_error { window fname text } {
   
    global igd_windowToplevel 

    Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
	    "\n ERROR while trying to write into the file $fname: \n \n $text \n"
}


#############################################################################
# Save the PostScript version of the graph on window's canvas.
# which = canvas then save the entire canvas; which = viewable then save the
# viewable region only. 
#
# The function calculates the best way of fitting the picture on an 8x11
# paper (by scaling and/or rotating the picture). It saves a greyscale
# version of the picture. 
#############################################################################

proc Igd_SavePs { window fname } {

    global igd_windowToplevel igd_windowMouseTrackerID igd_windowDesc

    set c $igd_windowToplevel($window).c

    # hide the mouse tracker while the canvas is copied so it won't show
    # on the picture
    $c itemconfigure $igd_windowMouseTrackerID($window) -state hidden

    set w [winfo width $c]
    set h [winfo height $c]

    # note 1 pixel is .8 printers point. The paper size is 8x11 in,
    # we use 6x9 in from it. 6 in = 423 pp = 540 pix; 9in = 648 pp = 810 pix.

    if { $w <= 540 && $h <= 810 } {
	# canvas fits onto the paper as it is.
	if { [catch {$c postscript -colormode gray -file $fname} result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    } elseif { $w <= 810 && $h <= 540 } {
	# canvas fits onto the paper if rotated.
	if { [catch {$c postscript -colormode gray -rotate 1 -file $fname} \
		result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    } elseif { double($h)/ double($w) > 1.5 } {
	# canvas is much taller than wide: scale wrt height
	if { [catch {$c postscript -colormode gray -pageheight 9i \
		-file $fname} result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    } elseif { double($w)/ double($h) > 1.5 } {
	# canvas is much wider than high: scale wrt width AND rotate
	if { [catch {$c postscript -colormode gray -pagewidth 9i -rotate 1 \
		-file $fname} \
		result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    } elseif { $h >= $w } {
	# canvas is a little higher than wide: scale wrt width
	if { [catch {$c postscript -colormode gray -pagewidth 6i \
		-file $fname} result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    } else {
	# $h < $w: scale wrt height AND rotate
	if { [catch {$c postscript -colormode gray -pageheight 6i -rotate 1 \
		-file $fname} \
		result] } {
	    Igd_postscript_error $window $result
	    set return_value 0
	} else {
	    set return_value 1
	}
    }

    # bring back the mouse tracker
    $c itemconfigure $igd_windowMouseTrackerID($window) -state normal

    return $return_value
}

#############################################################################
# Error message when saving the postscript.
#############################################################################

proc Igd_postscript_error { window fname text } {
    
    global igd_windowToplevel 

    Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
	    "\n ERROR while trying to save the PostScript version of the\
	    canvas into file $fname: \n \n $text \n"
}

