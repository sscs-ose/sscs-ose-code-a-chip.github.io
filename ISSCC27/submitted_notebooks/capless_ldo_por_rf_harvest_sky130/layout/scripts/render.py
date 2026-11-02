import klayout.db as db, klayout.lay as lay
v = lay.LayoutView()
v.load_layout("mag/ldo_top.gds", True)
v.max_hier()
v.set_config("background-color", "#ffffff")
v.set_config("grid-visible", "false")
v.zoom_fit()
v.save_image("mag/ldo_top.png", 1400, 1900)
print("ok")
