source /opt/eda/pdks-openram/ciel/sky130/versions/e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066/sky130A/libs.tech/netgen/setup.tcl

# Netgen's SPICE M-device parser names these primitive terminals, rather
# than numbering them. Preserve the prior property policy; correct only
# the drain/source permutation request for the short extracted aliases.
foreach dev {nfet_01v8 pfet_01v8_hvt} {
    foreach circuit {1 2} {
        if {[lsearch [set cells${circuit}] $dev] >= 0} {
            permute "-circuit${circuit} $dev" drain source
            property "-circuit${circuit} $dev" parallel enable
            property "-circuit${circuit} $dev" parallel {l critical}
            property "-circuit${circuit} $dev" parallel {w add}
            property "-circuit${circuit} $dev" tolerance {w 0.01} {l 0.01}
            property "-circuit${circuit} $dev" delete as ad ps pd mult sa sb sd nf nrd nrs area perim topography
        }
    }
}
