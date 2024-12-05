#############################################################################
# Enable the connection with C application.
# Introduce new buttons bindings and variables.
#############################################################################

proc Igd_EnableCAppl { window } {

    global igd_windowToplevel igd_windowWaitForClick igd_windowCApplEnabled \
	    igd_windowTextEntered igd_windowCmsgText

    set toplevel_name $igd_windowToplevel($window)

    set cont [button $toplevel_name.mbar.cont -text Continue \
	    -command "Igd_CApplContinue $toplevel_name"]
    set enter [button $toplevel_name.mbar.text -text "Enter text" \
	    -command "Igd_CApplEnterText $toplevel_name"]
    set reset [button $toplevel_name.mbar.reset -text Reset \
	    -command "Igd_CApplResetGraph $toplevel_name"]
    set cmsg [button $toplevel_name.mbar.cmsg -text "Msg from C" \
	    -command "Igd_CApplCmsg $toplevel_name"]
    
    pack $cmsg $reset $enter $cont -side right

    # reconfigure command bound to quit window menu button
    $toplevel_name.mbar.window.menu entryconfigure last \
	    -command "Igd_CApplQuitWindow $window"

    set igd_windowTextEntered($window) ""
    set igd_windowWaitForClick($window) 0
    set igd_windowCApplEnabled($window) 1
    set igd_windowCmsgText($window) ""

}    

#############################################################################
# Disable C connection. Do exactly the opposit of Igd_EnableCAppl.
#############################################################################

proc Igd_DisableCAppl { window } {

    global igd_windowToplevel igd_windowWaitForClick igd_windowCApplEnabled \
	    igd_windowTextEntered igd_windowCmsgText

    set toplevel_name $igd_windowToplevel($window)

    unset igd_windowCmsgText($window)
    set igd_windowCApplEnabled($window) 0
    unset igd_windowWaitForClick($window) 
    unset igd_windowTextEntered($window)
    
    $toplevel_name.mbar.window.menu entryconfigure last \
	    -command "Igd_QuitWindow $window"

    destroy $toplevel_name.mbar.cmsg
    destroy $toplevel_name.mbar.reset
    destroy $toplevel_name.mbar.text
    destroy $toplevel_name.mbar.cont
}    


#############################################################################
# Set igd_windowWaitForClick to 1. Commands from the 
# intermediary are held up until the 'Continue' button is pressed.
#############################################################################

proc Igd_CApplWaitForClick { window } {

    global igd_windowWaitForClick

    set igd_windowWaitForClick($window) 1
    Igd_PrintMsg $window "Press the Continue button...."
}

##############################################################################
# The 'Continue' button has been pressed. If igd_windowDesc(wait_for_click, )
# is set, send a message to the intermediary.
##############################################################################

proc Igd_CApplContinue { toplevel_name } {

    global igd_windowWaitForClick igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name)

    if { $igd_windowWaitForClick($window) == 1 } {
	set igd_windowWaitForClick($window) 0
	
	puts stdout "90100"
	puts stdout "$window"
	flush stdout
	Igd_PrintMsg $window "Continue has been pressed...."
    }
}

##############################################################################
# Open a text widget. When the user clicks on the Done button the contents
# of the widget is sent back to the intermediary for interpretation.
##############################################################################

proc Igd_CApplEnterText { toplevel_name } {

    global button3 igd_windowTextEntered igd_windowFromToplevel igd_windowTitle

    # the name of the text window is .text_$window. if this window is 
    # already open, do nothing

    set window $igd_windowFromToplevel($toplevel_name)
    if { [winfo exists .text_$window] } { return }

    # create a toplevel window for the frame that holds the text widget
    # and the function buttons
    set f [toplevel .text_$window -class frame]
    wm title $f "Enter text for window $igd_windowTitle($window)"
    set top [frame $f.top -bd 1]
    set bottom [frame $f.bottom -bd 1]
    pack $top -side top -fill both -expand true
    pack $bottom -side top -fill x

    set txt [text $top.txt -bd 1 -setgrid true -wrap none \
	    -height 12 -width 50 \
	    -xscrollcommand [list $top.xscroll set] \
	    -yscrollcommand [list $top.yscroll set]]
    set xscroll [scrollbar $top.xscroll -orient horizontal \
	    -command [list $txt xview]]
    set yscroll [scrollbar $top.yscroll -orient vertical \
	    -command [list $txt yview]]
    pack $xscroll -side bottom -fill x
    pack $yscroll -side right -fill y
    pack $txt -side left -fill both -expand true

    # create the buttons in the bottom frame.
    set button3 -1
    button $bottom.eval -text Evaluate -command "set button3 3"
    button $bottom.reset -text Reset -command "set button3 2"
    button $bottom.clear -text Clear -command "set button3 1"
    button $bottom.cancel -text Cancel -command "set button3 0"
    pack $bottom.eval $bottom.reset $bottom.clear $bottom.cancel -side left \
	    -padx 1 -pady 1 -expand true

    # insert text stored in igd_windowTextEntered
    $txt insert 1.0 $igd_windowTextEntered($window)

    # wait until Evaluate or Cancel is pressed
    while { $button3 <= 3 } {
	tkwait variable button3
	switch -exact -- $button3 {
	    3 {
		# evaluate: send message to intermediary
		puts stdout "90103"
		puts stdout "$window"
		set igd_windowTextEntered($window) [$txt get 1.0 "end -1 char"]
		set ln [string length $igd_windowTextEntered($window)]
		incr ln
		puts stdout "$ln"
		puts stdout "$igd_windowTextEntered($window)"
		flush stdout
		break
	    }
	    2 {
		$txt delete 1.0 end
		$txt insert 1.0 $igd_windowTextEntered($window)
	    }
	    1 {
		$txt delete 1.0 end
	    }
	    0 {
		break
	    }
	}
    }
    
    destroy $f
}

##############################################################################
# Send a request to the intermediary to send window desc and the graph 
# it currently stores again.
##############################################################################

proc Igd_CApplResetGraph { toplevel_name } {
    
    global igd_windowFromToplevel

    set window $igd_windowFromToplevel($toplevel_name)

    puts stdout "90104"
    puts stdout "$window"
    flush stdout
}

##############################################################################
# Bound to the Msg from C menubutton, this functions opens a message window 
# (if not yet open) and puts the contents of igd_windowCmsgText in it.
##############################################################################

proc Igd_CApplCmsg { toplevel_name } {

    global button2 igd_windowFromToplevel igd_windowTitle igd_windowCmsgText

    # the name of the message window is .cmsg_$window. if this window is
    # already open, do nothing.

    set window $igd_windowFromToplevel($toplevel_name)
    if { [winfo exists .cmsg_$window] } { return }

    set f [toplevel .cmsg_$window -class frame]
    wm title $f "Message from the C appl ($igd_windowTitle($window))"
    set top [frame $f.top -bd 1 -relief ridge]
    set bottom [frame $f.bottom -bd 1 -relief ridge]
    pack $top -side top -fill both -expand true
    pack $bottom -side top -fill x
    
    set msg [text $top.msg -bd 1 -setgrid true -wrap word -height 10 \
	-width 40 -yscrollcommand [list $top.yscroll set]]
    set yscroll [scrollbar $top.yscroll -orient vertical \
	    -command [list $msg yview]]
    pack $yscroll -side right -fill y
    pack $msg -side left -fill both -expand true
    
    # there is just one "Done" button in the bottom frame
    set button2 -1
    button $bottom.done -text Done -command "set button2 0"
    pack $bottom.done -padx 1 -pady 1 -expand true
    
    #insert message stored in igd_windowCmsgText
    $msg insert 1.0 $igd_windowCmsgText($window)

    #wait until Done is pressed 
    while { $button2 < 0 } {
	tkwait variable button2
    }
    destroy $f
}

##############################################################################
# Clear, set and append message in the Cmsg window.
##############################################################################

proc Igd_CApplClearCmsg { window } {

    global igd_windowCmsgText

    set igd_windowCmsgText($window) ""
    if { [winfo exists .cmsg_$window] } {
	.cmsg_$window.top.msg delete 1.0 end
    }
}

proc Igd_CApplSetCmsg { window txt } {

    global igd_windowCmsgText

    set igd_windowCmsgText($window) $txt
    if { [winfo exists .cmsg_$window] } {
	.cmsg_$window.top.msg delete 1.0 end
	.cmsg_$window.top.msg insert 1.0 $txt
    }
}

proc Igd_CApplAppendCmsg { window txt } {

    global igd_windowCmsgText

    append igd_windowCmsgText($window) $txt
    if { [winfo exists .cmsg_$window] } {
	.cmsg_$window.top.msg insert end $txt
    }
}

##############################################################################
# This function is bound to the Quit button. It sends a message to the
# intermediary that the user wants to terminate the graph drawing 
# application. The intermediary acknowledges this by invokling the 
# original Igd_QuitAll function.
##############################################################################

proc Igd_CApplQuitAll {} {

    puts stdout "90102"
    flush stdout
    exit
}


##############################################################################
# This function is bound to the "Quit from window" button. It sends a 
# message to the intermediary, which will acknowledge it by invoking the
# original Igd_QuitWindow function.
##############################################################################

proc Igd_CApplQuitWindow { window } {

    puts stdout "90101"
    puts stdout "$window"
    flush stdout
}

##############################################################################
##############################################################################
####   These are the basic library functions that need to be modified
####   when IGD is linked to an outside application.
##############################################################################
##############################################################################

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

