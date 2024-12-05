set pdk_root $env(PDK_ROOT)

source eda/sky130.magicrc
gds read design/gds_25c/cm_ota_align/CURRENT_MIRROR_OTA_0.gds
load CURRENT_MIRROR_OTA_0
extract unique
extract all
ext2spice
exit

