"""Native OpenROAD probe: PG check with geometry-preserving SBox directions.

Only the two known horizontal ground bridge boxes may change their direction
metadata. Never modify coordinates, nets, macro pins or published ODB/GDS.
"""
import argparse
import json


def bridge_targets(units):
    return {tuple(round(v*units) for v in box) for box in (
        (636.8,213.52,639.14,214.12),(1556.4,53.52,1560.74,54.12))}


if __name__=='__main__':
    from pathlib import Path
    import odb
    import openroad
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--odb',required=True);p.add_argument('--lib',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    tech=openroad.Tech();design=openroad.Design(tech)
    design.evalTclString('read_liberty {'+a.lib+'}')
    design.readDb(a.odb);block=design.getBlock()
    targets=bridge_targets(block.getDbUnitsPerMicron())
    changes=[]
    ground=block.findNet('VGND')
    for swire in ground.getSWires():
        for box in list(swire.getWires()):
            if box.isVia() or box.getTechLayer().getName()!='met4':continue
            bounds=(box.xMin(),box.yMin(),box.xMax(),box.yMax())
            if bounds not in targets:continue
            new=odb.dbSBox_create(swire,box.getTechLayer(),*bounds,'STRIPE',odb.dbSBox.HORIZONTAL)
            actual=(new.xMin(),new.yMin(),new.xMax(),new.yMax())
            if actual!=bounds:raise ValueError('direction normalization changed metal geometry')
            changes.append(dict(bounds_dbu=bounds,before_direction=box.getDirection(),after_direction=new.getDirection()))
            odb.dbSBox.destroy(box)
    if len(changes)!=2:raise ValueError('exactly two known bridge metadata changes required')
    rails={}
    for rail in ('VPWR','VGND'):
        try:
            design.evalTclString('check_power_grid -net '+rail)
            rails[rail]='PASS'
        except Exception as error:rails[rail]='FAIL: '+str(error)
    report=dict(status='PG_CONNECTED_EQUIVALENT_GEOMETRY' if all(v=='PASS' for v in rails.values()) else 'PG_CHECK_REMAINS_FAILED',
        rails=rails,changes=changes,geometry_changed=False,published_views_changed=False,
        scope='In-memory explicit horizontal SBox direction for two ground bridges; same exact metal bounds. '
              'Default virtual sources; connectivity only, no padframe, IR/EM or transistor body qualification.')
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('AUTOMX_CHIP_PG_METADATA_DONE')
