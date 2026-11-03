"""KLayout 위반 DB (.lyrdb) → 규칙별 위반 개수 (개수 0 인 규칙은 뺌). 쓰임: python lyrdb_sum.py <file.lyrdb>"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter

root = ET.parse(sys.argv[1]).getroot()
desc = {c.findtext('name'): (c.findtext('description') or '').strip() for c in root.iter('category')}
n = Counter((it.findtext('category') or '').strip("'") for it in root.find('items').iter('item'))
print(f"total {sum(n.values())}")
for k, v in sorted(n.items()):
    print(f"{v:6d}  {k:24s} {desc.get(k, '')[:90]}")
