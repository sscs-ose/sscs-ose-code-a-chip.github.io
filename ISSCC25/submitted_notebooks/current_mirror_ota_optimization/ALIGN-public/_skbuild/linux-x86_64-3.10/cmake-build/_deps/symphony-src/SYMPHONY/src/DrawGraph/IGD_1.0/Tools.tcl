#############################################################################
# Print out a short message into window's message field.
#############################################################################

proc Igd_PrintMsg { window message } {
    
    global igd_windowToplevel

    set toplevel_name $igd_windowToplevel($window)
    $toplevel_name.msgbar.msg configure -text $message
}

proc Igd_print_msg { toplevel_name message } {
    
    $toplevel_name.msgbar.msg configure -text $message
}


#############################################################################
# Pops up a message window with a specified text and an OK button below it to 
# kill the window. Used for displaying error messages and short information.
#     boxname: the path-name of the window
#     title: the title of the window
#     aspect: the aspect ratio of the window
#     text: the text to be displayed in the window
#############################################################################

proc Igd_message_box { boxname title aspect put_down text } {

    toplevel $boxname -class frame
    wm title $boxname $title
    if { $put_down } {
	set geom [winfo geometry [winfo parent $boxname]]
	set l [split $geom x+]
	set horiz [expr int([lindex $l 0] / double(2) - 120)]
	set vert [expr int([lindex $l 1] / double(2) - 70)]
	wm geometry $boxname +[expr [lindex $l 2] + $horiz]+[expr [lindex $l 3]+$vert]
    }
    
    set top [frame $boxname.top -bd 3 -relief groove]
    set bottom [frame $boxname.bottom -bd 1]
    pack $top $bottom -side top -fill x

    message $top.m -text $text -aspect $aspect
    pack $top.m -expand true
    button $bottom.ok -text OK -command "destroy $boxname"
    pack $bottom.ok 

    tkwait visibility $boxname
    grab set $boxname
    
    # wait until window is destroyed
    tkwait window $boxname
}

#############################################################################
# Create a dialog box.
#      boxname: window path name of the dialog box
#      title: the title of the window
#      args: a collection of three-element lists (the first element is the 
#	     text printed on the left, the second element is the string
#            that is going to be printed into the entry widget, and the 
#            third element is the length of the entry widget.)
# Buttons: Done, Reset, Clear, Cancel.
# If Done is pressed, a list of strings currently in the entry widgets 
#      returned. If there is only one entry, <Return> is the same as Done.
# If Reset is pressed the entries will be filled up with the original strings.
# If Clear is pressed, the contents of all the entry widgets are erased.
# If cancel is pressed, "CANCEL" is returned. 
#############################################################################

proc Igd_dialog_box { box_name title args } {

    global button1 var

    # Create a toplevel window for the dialog box and divide it into two
    # frame widgets that hold the input and the buttons, respectively.
    toplevel $box_name -class dialog
    wm title $box_name $title
    set top [frame $box_name.top -bd 3 -relief groove]
    set bottom [frame $box_name.bottom -bd 1]
    pack $top $bottom -side top -fill x

    # Define a frame for each argument, with a label and an entry widget 
    # in it. 
    set arg_num 0
    foreach arg $args {
	set text [lindex $arg 0]
	set var($arg_num) [lindex $arg 1]
	frame $top.$arg_num
	pack $top.$arg_num -side top -fill x -padx 1m -pady 1m
	label $top.$arg_num.left -text $text
	entry $top.$arg_num.right -relief sunken -width [lindex $arg 2] \
		-textvariable var($arg_num)
	pack $top.$arg_num.left -side left -anchor w
	pack $top.$arg_num.right -side right -anchor e
	incr arg_num
    }

    # In the bottom frame, four buttons are created, Done, Reset, Clear and
    # Cancel. The return_list is the return value of the procedure.
    set button1 -1
    button $bottom.done -text Done -command "set button1 3"
    button $bottom.reset -text Reset -command "set button1 2"
    button $bottom.clear -text Clear -command "set button1 1"
    button $bottom.cancel -text Cancel -command "set button1 0"
    pack $bottom.done $bottom.reset $bottom.clear $bottom.cancel -side left \
	    -padx 1 -pady 1 -expand true

    # If there is only one entry, then <Return> will be the same as Done.
    if { $arg_num == 1 } {
	bind $top.0.right <Return> "set button1 3"
    }

    # Confine keyboard and mouse events to the dialog box.
    grab set $box_name

    # Wait until Done or Cancel is pressed...
    while { $button1 <= 3 } {
	# Wait until a button is pressed 
	tkwait variable button1
	switch -exact -- $button1 {
	    3 {	
		set return_list {}
		for { set i 0 } { $i < $arg_num } { incr i } {
		    lappend return_list $var($i) ; set var($i) ""
		}
		# break out from while loop
		break		
	    }
	    2 {
		for { set i 0 } { $i < $arg_num } { incr i } {
		    set var($i) [lindex [lindex $args $i] 1]
		}
	    }
	    1 {	
		for { set i 0 } { $i < $arg_num } { incr i } {
		    set var($i) ""
		}
	    }
	    0 { 
		set return_list CANCEL
		# break out from while loop
		break
	    }
	}
    }

    # Get rid of the dialog box, and return 
    destroy $box_name
    return $return_list
}

#############################################################################
# Similar to dialog_box, just it allows two kinds of arguments.
# The first type of arg is the same entry type as before: it is a list of
# the following: the keyword "entry", the text printed to the left of the
# entry widget, the string displayed in the entry widget and then the length
# of the entry widget. When Done is pressed, the string in the entry 
# widget is returned.
# The second type of arg is a label followed by an arbitrary number of radio
# buttons. It is a list of the following; the keyword "radio", the text 
# printed to the left of the radio buttons, which radio button to highlight
# when displaying this dialog box, and then a list of the labels 
# corresponding to the radio buttons. There will be as many radio buttons
# created as labels given in this latter list. When Done is pressed, the
# number of the highlighted radio button is returned (numbering starts 
# from 0).
#
# Use the previous dialog box if only entry type args are needed.
#
# The Done, Reset, Clear and Cancel buttons work exactly the same way 
# as for the simple dialog box. 
#############################################################################

proc Igd_dialog_box2 { box_name title args } {

    global button var

    # Create a toplevel window for the dialog box and divide it into two
    # frame widgets that hold the input and the buttons, respectively.
    toplevel $box_name -class dialog
    wm title $box_name $title
    set top [frame $box_name.top -bd 3 -relief groove]
    set bottom [frame $box_name.bottom -bd 1]
    pack $top $bottom -side top -fill x
    
    # Define a frame for each argument, with a label and an entry widget 
    # in it for the "entry" types and with a label and radiobuttons in it
    # for the "radio" types
    set arg_num 0
    foreach arg $args {
	set type($arg_num) [lindex $arg 0]
	set text [lindex $arg 1]
	frame $top.$arg_num
	pack $top.$arg_num -side top -fill x -padx 1m -pady 1m
	label $top.$arg_num.left -text $text
	pack $top.$arg_num.left -side left -anchor w

	switch -exact -- $type($arg_num) {
	    entry {
		set var($arg_num) [lindex $arg 2]
		entry $top.$arg_num.right -relief sunken \
			-width [lindex $arg 3] -textvariable var($arg_num)
		pack $top.$arg_num.right -side right -anchor e
	    }
	    radio {
		set var($arg_num) [lindex $arg 2]
		set radio_num 0
		set radio_list [lindex $arg 3]
		foreach text $radio_list {
		    radiobutton $top.$arg_num.right$radio_num -text $text \
			    -variable var($arg_num) -value $radio_num
		    pack $top.$arg_num.right$radio_num -side left
		    incr radio_num
		}
	    }
	}
	incr arg_num
    }

    # In the bottom frame, four buttons are created, Done, Reset, Clear and
    # Cancel. The return_list is the return value of the procedure.
    set button -1
    button $bottom.done -text Done -command "set button 3"
    button $bottom.reset -text Reset -command "set button 2"
    button $bottom.clear -text Clear -command "set button 1"
    button $bottom.cancel -text Cancel -command "set button 0"
    pack $bottom.done $bottom.reset $bottom.clear $bottom.cancel -side left \
	    -padx 1 -pady 1 -expand true


    # If there is only one arg and that is of type entry, then <Return> 
    #will be the same as Done.
    if { $arg_num == 1 || $radio_num == 0 } {
	bind $top.0.right <Return> "set button 3"
    }
    # Confine keyboard and mouse events to the dialog box.
    grab set $box_name

    # Wait until Done or Cancel is pressed...
    while { $button <= 3 } {
	# Wait until a button is pressed 
	tkwait variable button
	switch -exact -- $button {
	    3 {	
		set return_list {}
		for { set i 0 } { $i < $arg_num } { incr i } {
		    lappend return_list $var($i) 
		    if { $type($i) == "entry" } { set var($i) "" }
		}
		# break out from while loop
		break		
	    }
	    2 {
		for { set i 0 } { $i < $arg_num } { incr i } {
		    set var($i) [lindex [lindex $args $i] 2]
		}
	    }
	    1 {	
		for { set i 0 } { $i < $arg_num } { incr i } {
		    if { $type($i) == "entry" } { set var($i) "" }
		}
	    }
	    0 { 
		set return_list CANCEL
		# break out from while loop
		break
	    }
	}
    }

    # Get rid of the dialog box, and return 
    destroy $box_name
    return $return_list
}

#############################################################################
# Check whether the font 'font' is valid or not, calling xlsfont (and using
# gawk). Returns 1 if font is valid, 0 if not or if xlsfonts couldn't
# be executed for some reason.
#############################################################################

proc Igd_CheckFont { window font } {

    global igd_windowToplevel

    set f "*"
    append f $font 
    set result [catch {exec xlsfonts -o $f |& gawk "BEGIN{num=1} /unmatched/ {num=0; next file;} END{print num;}"} a]
    if { $result } {
	# catch caught an error
	Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
		"Execution of xlsfonts (or gawk) was \n \
		unsuccessful. If you wish, you can turn off \n \
		the option of checking the validity of input \n \
		fonts by setting the variable igd_applCheckFonts \n \
		to 0 in the routine Igd_StartUp. \n"
	return 0
    } else {
	if { $a == 0 } {
	    Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
		    "\nFont name not recognized by xlsfonts\n"
	    return 0
	} else {
	    return 1
	}
    }
}

############################################################################
# Checks whether the dash pattern given is valid or not. Returns 1 if valid,
# displays error message and returns 0 if not. igd_applDashPattern contains 
# the allowed dash pattern.
############################################################################

proc Igd_ValidDashPattern { window dash } {

    global igd_applDashPattern igd_windowToplevel

    if { ![regexp -- $igd_applDashPattern $dash] } {
	# dash doesn't match the dash pattern
	Igd_message_box $igd_windowToplevel($window).mbox error 500 1 \
		"\n      Invalid dash pattern!\n \
		A dash pattern must be a (probably \n \
		   empty) sequence of integers.\n"
	return 0
    } else {
	return 1
    }
}

############################################################################
############################################################################

proc Igd_max { number1 number2 } {

    set m [expr $number1 > $number2 ? $number1 : $number2]
    return $m
}

proc Igd_min { number1 number2 } {

    set m [expr $number1 < $number2 ? $number1 : $number2]
    return $m
}
