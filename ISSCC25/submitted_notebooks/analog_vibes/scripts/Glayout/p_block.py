from glayout.flow.pdk.mappedpdk import MappedPDK
from glayout.flow.pdk.sky130_mapped import sky130_mapped_pdk
from gdsfactory.cell import cell
from gdsfactory.component import Component
from gdsfactory import Component
from glayout.flow.primitives.fet import nmos, pmos, multiplier
from glayout.flow.pdk.util.comp_utils import evaluate_bbox, prec_center
from glayout.flow.pdk.util.snap_to_grid import component_snap_to_grid
from glayout.flow.pdk.util.port_utils import rename_ports_by_orientation
from glayout.flow.routing.straight_route import straight_route
from glayout.flow.routing.c_route import c_route
from glayout.flow.routing.L_route import L_route
from glayout.flow.primitives.guardring import tapring
from glayout.flow.pdk.util.port_utils import add_ports_perimeter, rename_ports_by_list
from glayout.flow.spice.netlist import Netlist
from glayout.flow.primitives.via_gen import via_stack
from gdsfactory.components import text_freetype, rectangle
from four_transistor_interdigitized import generic_4T_interdigitzed

@cell
def  p_block(
        pdk: MappedPDK,
        width: float = 4.5,
        length: float = 1,
        fingers: int = 1,
        ratio: int = 1,
        ) -> Component:
    """
    p_block for super class AB OTA

    """
    #top level component
    top_level = Component(name="p_block")
    top_kwargs = {
            "fingers": ratio*fingers,
            "width": width,
            "with_tie": True,
            "sd_rmult":3
            }
    bottom_kwargs = {
            "fingers": fingers,
            "width": width,
            "with_tie": True,
            "sd_rmult":3
            }

    p_block = generic_4T_interdigitzed(pdk, top_row_device = "pfet", bottom_row_device = "pfet", numcols = 2, length = length, with_substrate_tap = False, top_kwargs = top_kwargs, bottom_kwargs = bottom_kwargs)
    p_block_ref = top_level << p_block

    top_level << c_route(pdk, p_block.ports["top_A_0_gate_W"], p_block.ports["bottom_A_0_drain_W"], width1=0.29, width2=0.32, cwidth=0.32)
    top_level << c_route(pdk, p_block.ports["top_B_1_gate_E"], p_block.ports["bottom_B_1_drain_E"], width1=0.29, width2=0.32, cwidth=0.32)
    top_level << c_route(pdk, p_block.ports["bottom_A_0_gate_W"], p_block.ports["bottom_B_0_gate_W"])
    
    top_level << c_route(pdk, p_block.ports["top_A_0_source_W"], p_block.ports["top_B_0_source_W"])
    top_level << straight_route(pdk, p_block.ports["top_A_0_source_W"], p_block.ports["top_welltie_W_top_met_W"], glayer1='met1', width=0.6)
    top_level << c_route(pdk, p_block.ports["bottom_A_0_source_W"], p_block.ports["bottom_B_0_source_W"], extension=1)
    top_level << straight_route(pdk, p_block.ports["bottom_A_0_source_W"], p_block.ports["bottom_welltie_W_top_met_W"], glayer1='met1', width=0.6)
    
    top_level << straight_route(pdk, p_block.ports["top_welltie_S_top_met_S"], p_block.ports["bottom_welltie_N_top_met_N"], glayer1='met2', width=3)
    
    #adding lvt layer
    lvt_layer = (125,44)

    dimensions = evaluate_bbox(p_block)

    lvt_rectangle = rectangle(layer=lvt_layer, size=(dimensions[0], dimensions[1]))
    lvt_rectangle_ref = top_level << lvt_rectangle
    lvt_rectangle_ref.move(p_block.center).movex(-dimensions[0]/2).movey(-dimensions[1]/2)
    
    top_level.add_padding(
            layers=(pdk.get_glayer("nwell"),),
            default=pdk.get_grule("active_tap", "nwell")["min_enclosure"],
            )
    
    #Renaming Ports
    top_level.add_ports(p_block.get_ports_list())

    return component_snap_to_grid(rename_ports_by_orientation(top_level))
"""
p_block = p_block(sky130_mapped_pdk)
p_block.show()
magic_drc_result = sky130_mapped_pdk.drc_magic(p_block, p_block.name)
"""
