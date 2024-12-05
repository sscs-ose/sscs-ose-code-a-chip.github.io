#############################################################################
# Draw a node on window's canvas.
#     window: the identifier of the window
#     node: identifier of the node (can be any string)
#     x, y: coordinates of the middle of the node
#     label: the text displayed in the middle of the node
#     dash: the dash pattern of the node's outline
#     radius: the radius of the node
#
# Note: this function doesn't check that the node already exists or not!!!
#############################################################################

proc Igd_MakeNode { window node x y label dash radius } {

    global igd_windowToplevel igd_windowDesc\
	    igd_windowNodes igd_windowNodeCount igd_windowNodeNum \
	    igd_nodeCoord igd_nodeWidgetID igd_nodeDesc igd_nodeFromWidgetID \
	    igd_nodeEdges

    set tmp "$window,$node"

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
	
    # display the circle
    set circle_id [$c create oval [expr $x-$radius] [expr $y-$radius] \
	    [expr $x+$radius] [expr $y+$radius] -outline black \
	    -fill yellow -dash $dash -tags "circle node vertex"]
    # set the text displayed in the middle of the node
    if { $igd_windowDesc(disp_nodelabels,$window) } { 
	set text $label 
    } else {
	set text ""
    }
    # display the label
    set label_id [$c create text $x $y -text $text \
	    -font $igd_windowDesc(nodelabel_font,$window) \
	    -tags "label node vertex"]
    
    # set the variables describing this node
    set igd_nodeCoord(x,$tmp) $x
    set igd_nodeCoord(y,$tmp) $y
    
    set igd_nodeWidgetID(circle,$tmp) $circle_id
    set igd_nodeWidgetID(label,$tmp) $label_id
    
    set igd_nodeDesc(radius,$tmp) $radius
    set igd_nodeDesc(dash,$tmp) $dash
    set igd_nodeDesc(label,$tmp) $label
    
    set igd_nodeFromWidgetID(circle,$window,$circle_id) $node
    set igd_nodeFromWidgetID(label,$window,$label_id) $node

    set igd_nodeEdges(out,$tmp) {}
    set igd_nodeEdges(in,$tmp) {}

    # update window variables
    lappend igd_windowNodes($window) $node
    incr igd_windowNodeCount($window)
    incr igd_windowNodeNum($window)

    Igd_PrintMsg $window "Created node with identifier $node,\
	    label $label at position $x $y."
}


#############################################################################
# Delete a node on window's canvas.
#     window: the identifier of the window
#     node: the identifier of the node
# All the edges adjacent to this node will be deleted also.
# If the node has a weight, that will be deleted, too.
#
# Note: this routine doesn't check whether the node exists or not!
#############################################################################

proc Igd_DeleteNode { window node } {

    global igd_windowToplevel igd_windowNodes igd_windowNodeCount \
	    igd_nodeCoord igd_nodeWidgetID igd_nodeDesc \
	    igd_nodeFromWidgetID igd_nodeEdges

    set tmp "$window,$node"
    
    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
    
    # delete the weight of the node if exists
    if { [info exists igd_nodeWidgetID(weight,$tmp)] } {
	Igd_DeleteNodeWeight $window $node
    }
    
    # delete edges adjacent to this node
    foreach edge $igd_nodeEdges(out,$tmp) {
	Igd_DeleteEdge $window $edge
    }
    foreach edge $igd_nodeEdges(in,$tmp) {
	Igd_DeleteEdge $window $edge
    }
    
    # delete the circle and label corresponding to this node
    set circle_id $igd_nodeWidgetID(circle,$tmp)
    set label_id $igd_nodeWidgetID(label,$tmp)

    $c delete $circle_id $label_id
    
    # update node data structures
    unset igd_nodeCoord(x,$tmp) igd_nodeCoord(y,$tmp) \
	    igd_nodeWidgetID(circle,$tmp) igd_nodeWidgetID(label,$tmp) \
	    igd_nodeDesc(radius,$tmp) igd_nodeDesc(dash,$tmp) \
	    igd_nodeDesc(label,$tmp)\
	    igd_nodeFromWidgetID(circle,$window,$circle_id) \
	    igd_nodeFromWidgetID(label,$window,$label_id) \
	    igd_nodeEdges(out,$tmp) igd_nodeEdges(in,$tmp)
    
    # update window data structures -- delete node from windowNodes
    set pos [lsearch $igd_windowNodes($window) $node]
    if { $pos >= 0 } {
	set igd_windowNodes($window) \
		[lreplace $igd_windowNodes($window) $pos $pos]
    }
    
    incr igd_windowNodeCount($window) -1
    
    Igd_PrintMsg $window "Deleted node with identifier $node"
}


#############################################################################
# Display weight corresponding to a node. The weight is anchored to the upper 
# right corner of the node.
#     window: identifier of the window
#     node: identifier of the node
#     weight: text to be displayed in the weight
# 
# Note: this routine doesn't check whether a weight already exists for this
#       node or whether the node exists at all or not.
#############################################################################

proc Igd_MakeNodeWeight { window node weight } {

    global igd_windowToplevel igd_windowDesc \
	    igd_nodeCoord igd_nodeWidgetID igd_nodeDesc igd_nodeFromWidgetID

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
	
    set tmp "$window,$node"

    # the weight is anchored to the upper right corner of the node
    set xx [expr $igd_nodeCoord(x,$tmp) + $igd_nodeDesc(radius,$tmp)]
    set yy [expr $igd_nodeCoord(y,$tmp) - $igd_nodeDesc(radius,$tmp)]
    
    set weight_id [$c create text $xx $yy -text $weight -anchor sw \
	    -justify left -font $igd_windowDesc(nodeweight_font,$window) \
	    -tags "weight vertex"]
    # move this weight just above the label in the display list
    $c lower $weight_id
    $c raise $weight_id $igd_nodeWidgetID(label,$window,$node)
    
    # set node variables 
    set igd_nodeWidgetID(weight,$tmp) $weight_id
    set igd_nodeDesc(weight,$tmp) $weight
    set igd_nodeFromWidgetID(weight,$window,$weight_id) $node

    Igd_PrintMsg $window \
	    "Weight for node with identifier $node has been created"
}


#############################################################################
# Delete node weight. 
#     window: identifier of the window
#     node: identifier of the node
#
# Note: this routine doesn't check whether the weight exists or not.
#############################################################################

proc Igd_DeleteNodeWeight { window node } {

    global igd_windowToplevel \
	    igd_nodeWidgetID igd_nodeDesc igd_nodeFromWidgetID

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
	
    set weight_id $igd_nodeWidgetID(weight,$window,$node)
    $c delete $weight_id

    # update node data structures
    unset igd_nodeWidgetID(weight,$window,$node) \
	    igd_nodeDesc(weight,$window,$node) \
	    igd_nodeFromWidgetID(weight,$window,$weight_id)

    Igd_PrintMsg $window \
	    "Weight of node with identifier $node has been deleted"
}


#############################################################################
# The following short functions change the text in node's label, the 
# outline and the radius of the node, and the text in node's weight.
#     window: identifier of the window
#     node: identifier of the node
#     new_...: the new text for label or weight, the new dash pattern or 
#              new radius
#
# Note: this routine doesn't check whether the corresponding node/label/
#       weight exists or not.
#############################################################################

proc Igd_ChangeOneNodeLabel { window node new_text } {
    
    global igd_windowToplevel igd_nodeWidgetID igd_nodeDesc

    set c $igd_windowToplevel($window).c
    $c itemconfigure $igd_nodeWidgetID(label,$window,$node) -text $new_text
    set igd_nodeDesc(label,$window,$node) $new_text

    Igd_PrintMsg $window "Changed label for node with identifier $node"
}


proc Igd_ChangeOneNodeDash { window node new_dash } {
    
    global igd_windowToplevel igd_nodeWidgetID igd_nodeDesc
    
    set c $igd_windowToplevel($window).c
    $c itemconfigure $igd_nodeWidgetID(circle,$window,$node) -dash $new_dash
    set igd_nodeDesc(dash,$window,$node) $new_dash

    Igd_PrintMsg $window "Changed dash pattern for node with identifier $node"
}

    
proc Igd_ChangeOneNodeRadius { window node new_radius } {

    global igd_windowToplevel igd_nodeCoord igd_nodeWidgetID igd_nodeDesc

    set c $igd_windowToplevel($window).c
    set tmp "$window,$node"
    
    # the scaling factor is the ratio of the new and the old radius
    # set sf [expr double($new_radius) / double($igd_nodeDesc(radius,$tmp))]
    # $c scale $igd_nodeWidgetID(circle,$tmp) \
    #     $igd_nodeCoord(x,$tmp) $igd_nodeCoord(y,$tmp) $sf $sf
    
    $c coords $igd_nodeWidgetID(circle,$tmp) \
	    [expr $igd_nodeCoord(x,$tmp) - $new_radius] \
	    [expr $igd_nodeCoord(y,$tmp) - $new_radius] \
	    [expr $igd_nodeCoord(x,$tmp) + $new_radius] \
	    [expr $igd_nodeCoord(y,$tmp) + $new_radius] 

    set igd_nodeDesc(radius,$tmp) $new_radius

    # need to move node weight to the upper right corner of the node
    if { [info exists igd_nodeWidgetID(weight,$tmp)] } {
	$c coords $igd_nodeWidgetID(weight,$tmp) \
		[expr $igd_nodeCoord(x,$tmp) + $new_radius] \
		[expr $igd_nodeCoord(y,$tmp) - $new_radius]
    }

    Igd_PrintMsg $window "Changed radius for node with identifier $node"
}


proc Igd_ChangeOneNodeWeight { window node new_text } {

    global igd_windowToplevel igd_nodeWidgetID igd_nodeDesc

    set c $igd_windowToplevel($window).c
    $c itemconfigure $igd_nodeWidgetID(weight,$window,$node) -text $new_text
    set igd_nodeDesc(weight,$window,$node) $new_text

    Igd_PrintMsg $window "Changed weight for node with identifier $node"
}


#############################################################################
# Create an edge between the given endpoints.
#     window: identifier of the window
#     edge: identifier of the edge
#     tail, head: node identifiers of the endpoints of the edge
#     dash: dash pattern to be used to display the line between tail and head
#
# Note: this routine doesn't check whether an edge with the same identifier
#       already exists or not, neither it checks whether the given 
#       endpoints exist or not.
#############################################################################

proc Igd_MakeEdge { window edge tail head dash } {

    global igd_windowToplevel igd_windowEdges igd_windowEdgeNum \
	    igd_windowDesc igd_nodeCoord igd_nodeEdges \
	    igd_edgeEnds igd_edgeWidgetID igd_edgeDesc igd_edgeFromWidgetID

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
	
    # display the line and lower it in the display list so that the ends
    # hide under the nodes
    set line_id [$c create line \
	    $igd_nodeCoord(x,$window,$tail) $igd_nodeCoord(y,$window,$tail) \
	    $igd_nodeCoord(x,$window,$head) $igd_nodeCoord(y,$window,$head) \
	    -dash $dash -tags "edge line"]

    # the edge is moved below all the nodes on the display list
    $c lower $line_id vertex

    # set the variables describing this edge
    set igd_edgeEnds(tail,$window,$edge) $tail
    set igd_edgeEnds(head,$window,$edge) $head
    
    set igd_edgeWidgetID(line,$window,$edge) $line_id
    set igd_edgeDesc(dash,$window,$edge) $dash
    set igd_edgeFromWidgetID(line,$window,$line_id) $edge

    # update node and window variables
    lappend igd_nodeEdges(out,$window,$tail) $edge
    lappend igd_nodeEdges(in,$window,$head) $edge
    
    lappend igd_windowEdges($window) $edge
    incr igd_windowEdgeNum($window)

    Igd_PrintMsg $window "Created edge with identifier $edge, between nodes\
	    $tail and $head"
}


#############################################################################
# Deletes an edge.
#     window: identifier of the window
#     edge: identifier of the edge to be deleted.
#
# Note: this routine doesn't check whether the given edge exists or not.
#############################################################################

proc Igd_DeleteEdge { window edge } {

    global igd_windowToplevel igd_windowEdges igd_nodeEdges igd_edgeEnds \
	    igd_edgeWidgetID igd_edgeDesc igd_edgeFromWidgetID

    set tmp "$window,$edge"
    
    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c

    # delete the weight of the edge if exists
    if { [info exists igd_edgeWidgetID(weight,$tmp)] } {
	Igd_DeleteEdgeWeight $window $edge
    }
    
    # delete the line corresponding to this edge
    set line_id $igd_edgeWidgetID(line,$tmp)
    $c delete $line_id

    # update node and window data structures
    set tail $igd_edgeEnds(tail,$tmp)
    set head $igd_edgeEnds(head,$tmp)
    set pos [lsearch $igd_nodeEdges(out,$window,$tail) $edge]
    set igd_nodeEdges(out,$window,$tail) \
	    [lreplace $igd_nodeEdges(out,$window,$tail) $pos $pos]
    set pos [lsearch $igd_nodeEdges(in,$window,$head) $edge]
    set igd_nodeEdges(in,$window,$head) \
	    [lreplace $igd_nodeEdges(in,$window,$head) $pos $pos]

    set pos [lsearch $igd_windowEdges($window) $edge]
    set igd_windowEdges($window) [lreplace $igd_windowEdges($window) $pos $pos]

    # update edge data structures
    unset igd_edgeEnds(tail,$tmp) igd_edgeEnds(head,$tmp) \
	    igd_edgeWidgetID(line,$tmp) igd_edgeDesc(dash,$tmp) \
	    igd_edgeFromWidgetID(line,$window,$line_id)

    Igd_PrintMsg $window \
	    "Deleted edge with identifier $edge, between nodes $tail and $head"
}

#############################################################################
# Display weight corresponding to an edge.
#     window: identifier of the window
#     edge: identifier of the edge
#     weight: the text to be displayed in the weight
#
# Note: this routine doesn't check whether a weight already exists for 
#       this edge or whether the edge exists at all or not.
#############################################################################

proc Igd_MakeEdgeWeight { window edge weight } {
    
    global igd_windowToplevel igd_windowDesc igd_nodeCoord igd_edgeEnds \
	    igd_edgeWidgetID igd_edgeDesc igd_edgeFromWidgetID

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c

    set tmp "$window,$edge"
    set tail $igd_edgeEnds(tail,$tmp) ; set head $igd_edgeEnds(head,$tmp)

    # the weight is going to be placed north-east from the middle of the edge
    set xx [expr ($igd_nodeCoord(x,$window,$tail) \
	    + $igd_nodeCoord(x,$window,$head)) /2]
    set yy [expr ($igd_nodeCoord(y,$window,$tail) \
	    + $igd_nodeCoord(y,$window,$head)) /2]

    set weight_id [$c create text $xx $yy -text $weight -anchor sw \
	    -justify left -font $igd_windowDesc(edgeweight_font,$window) \
	    -tags "weight edge"]

    # move the weight just above the line in the display list
    $c lower $weight_id
    $c raise $weight_id $igd_edgeWidgetID(line,$window,$edge)

    # set edge variables
    set igd_edgeWidgetID(weight,$tmp) $weight_id
    set igd_edgeDesc(weight,$tmp) $weight
    set igd_edgeFromWidgetID(weight,$window,$weight_id) $edge

    Igd_PrintMsg $window "Weight for edge $edge between nodes $tail and $head\
	    has been created"
}

#############################################################################
# Delete edge weight. 
#     window: identifier of the window
#     edge: identifier of the edge
#
# Note: this routine doesn't check whether the weight exists or not.
#############################################################################

proc Igd_DeleteEdgeWeight { window edge } {

    global igd_windowToplevel \
	    igd_edgeEnds igd_edgeWidgetID igd_edgeDesc igd_edgeFromWidgetID

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c

    set tmp "$window,$edge"
	
    set weight_id $igd_edgeWidgetID(weight,$tmp)
    $c delete $weight_id

    # update edge data structures
    set tail $igd_edgeEnds(tail,$tmp) ; set head $igd_edgeEnds(head,$tmp)
    unset igd_edgeWidgetID(weight,$tmp) igd_edgeDesc(weight,$tmp) \
	    igd_edgeFromWidgetID(weight,$window,$weight_id)

    Igd_PrintMsg $window \
	    "Weight of edge with identifier $edge has been deleted"
}
    
#############################################################################
# The following short functions change the outline of an edge and the 
# text displayed in edge's weight.
#     window: identifier of the window
#     edge: identifier of the edge
#     new_...: the new dash pattern or text
#
# Note: this routine doesn't check whether the corresponding edge/weight
#       exists or not.
#############################################################################
	   
proc Igd_ChangeOneEdgeDash { window edge new_dash } {
    
    global igd_windowToplevel igd_edgeEnds igd_edgeWidgetID igd_edgeDesc
    
    set c $igd_windowToplevel($window).c
    $c itemconfigure $igd_edgeWidgetID(line,$window,$edge) -dash $new_dash
    set igd_edgeDesc(dash,$window,$edge) $new_dash

    Igd_PrintMsg $window "Changed dash pattern for edge $edge between nodes\
	    $igd_edgeEnds(tail,$window,$edge)\
	    and $igd_edgeEnds(head,$window,$edge)"
}


proc Igd_ChangeOneEdgeWeight { window edge new_text } {

    global igd_windowToplevel igd_edgeEnds igd_edgeWidgetID igd_edgeDesc

    set c $igd_windowToplevel($window).c
    $c itemconfigure $igd_edgeWidgetID(weight,$window,$edge) -text $new_text
    set igd_edgeDesc(weight,$window,$edge) $new_text

    Igd_PrintMsg $window "Changed weight for edge $edge between nodes\
	    $igd_edgeEnds(tail,$window,$edge)\
	    and $igd_edgeEnds(head,$window,$edge)"
}


#############################################################################
# Move a node on window's canvas
#     window: the identifier of the window
#     node: the identifier of the node
#     xdist, ydist: move the node by this much in the coordinate directions
# Edges adjacent to this node will be moved, too.
#
# Note: this routine doesn't check whether the node exists or not.
#############################################################################

proc Igd_MoveNode { window node xdist ydist } {

    global igd_windowToplevel igd_nodeCoord igd_nodeWidgetID igd_nodeEdges \
	    igd_edgeEnds igd_edgeWidgetID

    Igd_RaiseNode $window $node

    # figure out the path-name of the canvas
    set c $igd_windowToplevel($window).c
    
    set tmp "$window,$node"

    # round the distances into integer numbers 
    set xdist [expr round($xdist)]
    set ydist [expr round($ydist)]

    $c move $igd_nodeWidgetID(circle,$tmp) $xdist $ydist
    $c move $igd_nodeWidgetID(label,$tmp) $xdist $ydist
    if { [info exists igd_nodeWidgetID(weight,$tmp)] } {
	$c move $igd_nodeWidgetID(weight,$tmp) $xdist $ydist
    }

    # set new coordinates for the node
    set newx [incr igd_nodeCoord(x,$tmp) $xdist] 
    set newy [incr igd_nodeCoord(y,$tmp) $ydist]

    # move the edges adjacent to this node
    foreach edge $igd_nodeEdges(out,$tmp) {
	set head $igd_edgeEnds(head,$window,$edge)
	$c coords $igd_edgeWidgetID(line,$window,$edge) $newx $newy \
		$igd_nodeCoord(x,$window,$head) $igd_nodeCoord(y,$window,$head)
	# move the edge weights if any
	if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
	    $c coords $igd_edgeWidgetID(weight,$window,$edge) \
		    [expr ($newx + $igd_nodeCoord(x,$window,$head)) / 2] \
		    [expr ($newy + $igd_nodeCoord(y,$window,$head)) / 2]
	}
    }
    foreach edge $igd_nodeEdges(in,$tmp) {
	set tail $igd_edgeEnds(tail,$window,$edge)
	$c coords $igd_edgeWidgetID(line,$window,$edge) \
		$igd_nodeCoord(x,$window,$tail) \
		$igd_nodeCoord(y,$window,$tail) \
		$newx $newy 
	# move the edge weights if any
	if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
	    $c coords $igd_edgeWidgetID(weight,$window,$edge) \
		    [expr ($newx + $igd_nodeCoord(x,$window,$tail)) / 2] \
		    [expr ($newy + $igd_nodeCoord(y,$window,$tail)) / 2]
	}
    }

    Igd_PrintMsg $window "Moving node $node to position $newx,$newy."
}


#############################################################################
# Checks whether a node exists or not. It checks for the identifier of the
# node in igd_windowNodes.
#     window: identifier of the window
#     node: identifier of the node
# The function returns 1 if the node exists, 0 if not.
#############################################################################

proc Igd_ExistsNode { window node } {

    global igd_windowNodes

    set pos [lsearch $igd_windowNodes($window) $node]
    if { $pos >= 0 } {
	return 1
    } else {
	return 0
    }
}

#############################################################################
# Checks whether a edge exists or not. It checks for the identifier of the
# edge in igd_windowEdges.
#     window: identifier of the window
#     edge: identifier of the edge
# The function returns 1 if the edge exists, 0 if not.
#############################################################################

proc Igd_ExistsEdge { window edge } {

    global igd_windowEdges

    set pos [lsearch $igd_windowEdges($window) $edge]
    if { $pos >= 0 } {
	return 1
    } else {
	return 0
    }
}

#############################################################################
# Returns a list of edges (in the order they have been added) between the
# two nodes specified. (If there are no edges between these nodes, the list
# will be empty.)
#############################################################################

proc Igd_ExistsEdgeBetweenNodes { window n1 n2 } {

    global igd_windowEdges igd_edgeEnds 

    set candidate_list {}

    foreach edge $igd_windowEdges($window) {
	set e "$window,$edge"
	if { ( $igd_edgeEnds(tail,$e) == $n1 && \
		$igd_edgeEnds(head,$e) == $n2 ) || \
		( $igd_edgeEnds(tail,$e) == $n2 && \
		$igd_edgeEnds(head,$e) == $n1 ) } {
	    lappend candidate_list $edge
	}
    }
    
    return $candidate_list
}

#############################################################################
# Given a string which is supposed to be the label of one of the nodes 
# on window's canvas, return the id of the first node whose label matches
# the string or the empty string if there is no match.
#############################################################################

proc Igd_NodeFromLabel { window label } {

    global igd_windowNodes igd_nodeDesc

    set return_value ""

    foreach node $igd_windowNodes($window) {
	if { [string trim $igd_nodeDesc(label,$window,$node)] == \
		[string trim $label] } {
	    set return_value $node
	    break
	}
    }
    return $return_value
}


#############################################################################
# Raise the node (its circle, label and weight (if exists) above all
# the canvas items.
#############################################################################

proc Igd_RaiseNode { window node } {

    global igd_windowToplevel igd_nodeWidgetID

    set c $igd_windowToplevel($window).c

    $c raise $igd_nodeWidgetID(circle,$window,$node)
    $c raise $igd_nodeWidgetID(label,$window,$node)
    if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
	$c raise $igd_nodeWidgetID(weight,$window,$node)
    }
}

#############################################################################
# Lower the node under the other nodes (but above the edges).
#############################################################################

proc Igd_LowerNode { window node } {

    global igd_windowToplevel igd_nodeWidgetID

    set c $igd_windowToplevel($window).c

    if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
	$c lower $igd_nodeWidgetID(weight,$window,$node)
    }
    $c lower $igd_nodeWidgetID(label,$window,$node) vertex
    $c lower $igd_nodeWidgetID(circle,$window,$node) vertex
}


#############################################################################
# Returns a list of the node id's in the order the nodes are currently 
# displayed on the canvas.
#############################################################################

proc Igd_NodeOrderInDisplayList { window } {

    global igd_windowToplevel igd_windowNodeCount igd_windowEdges \
	    igd_windowMouseTrackerID igd_nodeFromWidgetID igd_nodeWidgetID

    set c $igd_windowToplevel($window).c
    set node_list {}
    set node_count $igd_windowNodeCount($window)
    
    if { $node_count > 0 } {
	# determine the canvas id of the circle of the lowest node
	if { [llength $igd_windowEdges($window)] > 0 } { 
	    set current_circle [$c find above edge] 
	} elseif { [info exists igd_windowMouseTrackerID($window)] } {
	    # mouse tracker is always the second lowest if exists
	    set current_circle \
		    [$c find above $igd_windowMouseTrackerID($window)]
	} else {
	    set current_circle [$c find above dummy]
	}

	set counter 0
	while { $counter < $node_count } {
	    set node $igd_nodeFromWidgetID(circle,$window,$current_circle)
	    lappend node_list $node
	    incr counter

	    # the next one on the display list is the label of the node and 
	    # possibly the weight
	    set label [$c find above $current_circle]
	    
	    if { [info exists igd_nodeWidgetID(weight,$window,$node)] } {
		set weight [$c find above $label]
		set current_circle [$c find above $weight]
	    } else {
		set current_circle [$c find above $label]
	    }
	}
    }
    return $node_list
}

#############################################################################
# Returns a list of the edge id's in the order the nodes are currently 
# displayed on the canvas.
#############################################################################

proc Igd_EdgeOrderInDisplayList { window } {

    global igd_windowToplevel igd_windowEdges igd_windowMouseTrackerID \
	    igd_edgeFromWidgetID igd_edgeWidgetID 

    set c $igd_windowToplevel($window).c
    set edge_list {}
    set edge_count [llength $igd_windowEdges($window)]
   
    if { $edge_count > 0 } {
	# determine the canvas id of the line of the lowest edge
	if { [info exists igd_windowMouseTrackerID($window)] } {
	    # mouse tracker is always the second lowest if exists
	    set current_line [$c find above $igd_windowMouseTrackerID($window)]
	} else {
	    set current_line [$c find above dummy]
	}
	
	set counter 0
	while { $counter < $edge_count } {
	    set edge $igd_edgeFromWidgetID(line,$window,$current_line)
	    lappend edge_list $edge
	    incr counter

	    # the next one on the display might be a weight
	    if { [info exists igd_edgeWidgetID(weight,$window,$edge)] } {
		set weight [$c find above $current_line]
		set current_line [$c find above $weight]
	    } else {
		set current_line [$c find above $current_line]
	    }
	}
    }
    return $edge_list
}
	    


#############################################################################
# This function returns a list of two elements: [list node_given_with_id \
# text] where node_given_with_id is 1 if node is given with its id, 0 if 
# it's given with its label, and "" if there is nothing in register regnum; 
# text is the node id, the label, or "" respectively.
#############################################################################

proc Igd_GetNodeFromRegister { window regnum } {

    global igd_windowRegisters igd_applSpacesPattern

    if { $igd_windowRegisters($regnum,node,$window) != "" } {
	if { [regexp -- $igd_applSpacesPattern \
		$igd_windowRegisters($regnum,label,$window)] == 0 } {
	    # label is not made up only of spaces
	    set text $igd_windowRegisters($regnum,label,$window)
	    set node_given_with_id 0
	} else {
	    set text $igd_windowRegisters($regnum,node,$window)
	    set node_given_with_id 1
	}
    } else {
	set text "" ; set node_given_with_id 0
    }
    
    return [list $node_given_with_id $text]
}

#############################################################################
# text is supposedly the node id or label of a node on window's canvas. 
# node_given_with_id tells whether the node is given with its id or
# with its label. This function checks whether the node exists or not, 
# and returns the node id if found or "" if it was invalid. 
# The function also prints error messages.
#############################################################################

proc Igd_IdentifyNode { window text node_given_with_id regnum } {

    global igd_windowToplevel igd_applSpacesPattern igd_windowRegisters

    set toplevel_name $igd_windowToplevel($window)

    # if text is left empty... error
    if { [regexp -- $igd_applSpacesPattern $text] } {
	# entry is all spaces
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n No node has been specified\n"
	return ""
    }

    # if the node id doesn't exist or the label doesn't have any corresponding 
    # node.... error
    if { ($node_given_with_id && ![Igd_ExistsNode $window $text]) ||\
	    ( !$node_given_with_id && \
	    [set node [Igd_NodeFromLabel $window $text]] == "") } {
	Igd_message_box $toplevel_name.mbox error 500 1 \
		"\n Node id or label doesn't exist\n"
	return ""
    }

    if { $regnum == 1 } {
	# if the node is from register 1 and was given by its label, and 
	# nodeFromLabel found an other node id with the same label, then set
	# the node back to the node in the register
	if { !$node_given_with_id && \
		$igd_windowRegisters(1,label,$window) == $text } {
	    set node $igd_windowRegisters(1,node,$window)
	} 
    } 
    if { $regnum == 2 } {
	# same for register 2
	if { !$node_given_with_id && \
		$igd_windowRegisters(1,label,$window) == $text } {
	    set node $igd_windowRegisters(1,node,$window)
	} 
    } 

    if { $node_given_with_id } { set node $text }

    return $node
}
