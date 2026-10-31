"""Keep the complete notebook narrative concise and its references explicit."""
from pathlib import Path
import json
import re
import nbformat


CITATIONS = {
    'theory': ('Attention formulation', [1]),
    'cim-edu-format-theory': ('Format specification', [2]),
    'cim-edu-ternary-theory': ('Ternary-weight background', [3]),
    'cim-edu-leaf-theory': ('Device models and process', [6]),
    'native-theory-design-flow': ('Physical implementation flow', [10, 11]),
    'native-theory-charge-sampling': ('Sampling and SAR background', [4]),
    'native-theory-sar-interface': ('SAR architecture and reused circuit/RTL', [4, 5]),
    'block-floorplan-runtime-guide': ('Implementation, extraction, and timing tools', [10, 11, 12]),
    'mha-ip-verify-guide': ('RTL simulation and synthesis tools', [8, 9]),
    'native-new-fc80dbb4': ('Co-simulation and SAR sources', [5, 7, 8]),
    'native-new-769a8093': ('Synthesis documentation', [9]),
    'native-new-7f88b3dd': ('Physical flow and layout tools', [10, 11, 13]),
    'native-theory-verification': ('Process and verification documentation', [6, 11, 12, 14, 15]),
    'native-new-b48e59fe': ('Extraction and netlist comparison', [14, 15]),
    'native-new-e803cdc7': ('RC extraction and static timing', [11, 12]),
}


def finalize_book(book, root):
    root = Path(root)
    policy = root/'data/notebook_editorial_policy.json'
    if not policy.is_file():
        return book
    removed = set(json.loads(policy.read_text())['remove_markdown_ids'])
    for cell in book.cells:
        if cell.id in removed and cell.cell_type != 'markdown':
            raise ValueError('Editorial cleanup cannot remove code: ' + cell.id)
    book.cells = [c for c in book.cells if c.id not in removed]
    by_id = {c.id: c for c in book.cells}
    roadmap = by_id.get('argument-roadmap')
    if roadmap:
        roadmap.source = roadmap.source.replace(
            'Original experiment numbers remain in detailed subsections. Earlier introductory\n'
            '    guides are retained together in an appendix so the main argument proceeds once.',
            'Original experiment numbers remain in detailed subsections.\n'
            '    [References](#references) collects the cited papers, format specification, reused IP, and tool documentation.')
    ledger = by_id.get('argument-appendix-implementation')
    if ledger:
        ledger.source = (
            '## Reproducibility and execution ledger\n\n'
            'The following cells retain the executable orchestration, tool receipts, and final artifact ledger. '
            'Their code order is preserved so Run All processes every native code cell exactly once.\n'
        )
    for cell in book.cells:
        if cell.cell_type == 'markdown' and cell.id.startswith('argument-'):
            cell.source = '\n'.join(line[4:] if line.startswith('    ') else line
                                    for line in cell.source.splitlines()) + '\n'
    tag_guide = by_id.get('native-restored-server-flow-review-guide')
    if tag_guide:
        tag_guide.source = '### Reports by run tag\n'
    for cell_id, (label, refs) in CITATIONS.items():
        cell = by_id.get(cell_id)
        if cell is None:
            continue
        sentence = label + ': ' + ', '.join(f'[[{n}]](#ref-{n})' for n in refs) + '.'
        if sentence not in cell.source:
            cell.source = cell.source.rstrip() + '\n\n' + sentence + '\n'
    cell = by_id.get('cim-edu-leaf-theory')
    origin = 'The 8T topology is defined by the project source `inputs/core_acquisition.spice`; the process reference documents its SKY130 devices.'
    if cell and origin not in cell.source:
        cell.source = cell.source.rstrip() + '\n\n' + origin + '\n'
    references = by_id.get('references')
    text = (root/'data/notebook_references.md').read_text()
    if references is None:
        references = nbformat.v4.new_markdown_cell(text, id='references')
    else:
        references.source = text
        book.cells.remove(references)
    book.cells.append(references)
    results = by_id.get('output-results-map')
    if results and '[References](#references)' not in results.source:
        results.source = results.source.rstrip() + '\n\n[References](#references)\n'
    book.metadata['presentation_structure'] = 'complete_design_flow_with_final_references'
    book.metadata['editorial_policy'] = 'data/notebook_editorial_policy.json'
    book.metadata['reference_count'] = 15
    return book


def apply(root):
    root = Path(root).resolve()
    for name in ('AutoMX_CIM_Code_a_Chip.ipynb', 'AutoMX_CIM_Code_a_Chip.executed.ipynb'):
        path = root/name
        if not path.is_file():
            continue
        book = nbformat.read(path, 4)
        code = [dict(c) for c in book.cells if c.cell_type == 'code']
        finalize_book(book, root)
        assert code == [dict(c) for c in book.cells if c.cell_type == 'code']
        nbformat.validate(book)
        temp = path.with_suffix('.editorial.ipynb')
        nbformat.write(book, temp)
        temp.replace(path)
        print('PRESENTATION_UPDATED', name, len(book.cells), 'cells;', len(code), 'unchanged code cells')


if __name__ == '__main__':
    import sys
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
