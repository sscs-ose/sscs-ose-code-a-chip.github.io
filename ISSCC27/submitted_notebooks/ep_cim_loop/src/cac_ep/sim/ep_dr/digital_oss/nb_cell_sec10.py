# col_blk from the open-source flow (section 8): the router reads route_oss/lef_fix/col_blk.lef instead of place/lef/col_blk.lef
# (the only difference: vrailp and vrailm are signal pins, not ground). Rebuild that copy from the new LEF so the blocked areas match the new layout.
import re
if 'col_blk' in globals().get('DIG_OSS', []):
    t = (LT / 'place/lef/col_blk.lef').read_text()
    t, n = re.subn(r'(PIN (?:vrailp|vrailm)\n\s+DIRECTION \w+ ;\n\s+USE )GROUND', r'\1SIGNAL', t)
    (LT / 'route_oss/lef_fix/col_blk.lef').write_text(t)
    print(f'route_oss/lef_fix/col_blk.lef rebuilt from place/lef/col_blk.lef ({n} pins set to USE SIGNAL)')
