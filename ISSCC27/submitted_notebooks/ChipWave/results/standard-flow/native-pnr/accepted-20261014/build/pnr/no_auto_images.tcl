# Optional ORFS image rendering uses a scene API absent from the installed OpenROAD.
rename gui::show nebula_gui_show
proc gui::show {script args} {
  if {[string match "*save_images.tcl*" $script]} {
    puts "OPTIONAL_GUI_IMAGES_SKIPPED: scene API mismatch; all physical/STA checks remain enabled."
    return
  }
  nebula_gui_show $script {*}$args
}
