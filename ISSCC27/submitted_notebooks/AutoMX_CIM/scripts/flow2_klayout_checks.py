"""KLayout zero-item reports require enabled rules, never exit status alone."""
from collections import Counter
import xml.etree.ElementTree as ET


def summarize(path):
    root=ET.parse(path).getroot()
    if root.tag!='report-database':raise ValueError('invalid KLayout report')
    definitions=root.find('categories')
    categories=list(definitions.iter('category')) if definitions is not None else []
    if not categories:raise ValueError('KLayout report has no enabled rule categories')
    items=list(root.iter('item'))
    return {'categories':len(categories),'violations':len(items),
        'violations_by_category':dict(Counter(row.findtext('category') for row in items))}


def full_groups_clean(path,groups):
    try:result=summarize(path)
    except ValueError:return False
    return result['violations']==0 and all(groups.get(name) is True for name in ('feol','beol','offgrid'))
