"""Apply the reviewed English wording without changing numerical implementation."""
from pathlib import Path
import base64
import json
import re
import nbformat

VIETNAMESE = re.compile(
    '[ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ'
    'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]'
)
SVG_DATA = re.compile(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)')


def translator(root):
    catalog = json.loads((Path(root)/'data/notebook_english.json').read_text())
    phases = [(phrases, re.compile('|'.join(re.escape(k) for k in
        sorted(phrases, key=len, reverse=True)))) for phrases in catalog['phases']]

    def plain(text):
        for phrases, pattern in phases:
            text = pattern.sub(lambda m: phrases[m[0]], text)
        return text

    def translate(text):
        text = plain(text)

        def svg(match):
            decoded = base64.b64decode(match[1]).decode('utf-8')
            return 'data:image/svg+xml;base64,' + base64.b64encode(plain(decoded).encode()).decode()

        return SVG_DATA.sub(svg, text)

    return translate


def translate_book(book, root):
    translate = translator(root)
    for cell in book.cells:
        cell.source = translate(cell.source)
    book.metadata['presentation_language'] = 'en'
    book.metadata['english_catalog'] = 'data/notebook_english.json'
    if (Path(root)/'data/notebook_editorial_policy.json').is_file():
        from scripts.finalize_notebook_presentation import finalize_book
        finalize_book(book, root)
    return book


def remaining_text(book, outputs=True):
    remaining = []

    def inspect(text, location):
        if VIETNAMESE.search(text):
            remaining.append({'location': location, 'text': text[:300]})
        for match in SVG_DATA.finditer(text):
            inspect(base64.b64decode(match[1]).decode('utf-8'), location + ':embedded-svg')

    def walk(value, location):
        if isinstance(value, str):
            inspect(value, location)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, location + ':' + str(i))
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in ('image/png', 'image/jpeg', 'application/pdf'):
                    walk(item, location + ':' + str(key))

    for cell in book.cells:
        inspect(cell.source, cell.id + ':source')
        if outputs:
            walk(cell.get('outputs', []), cell.id + ':output')
            walk(cell.get('attachments', {}), cell.id + ':attachment')
    return remaining


def apply(root):
    root = Path(root).resolve()
    path = root/'AutoMX_CIM_Code_a_Chip.ipynb'
    book = translate_book(nbformat.read(path, 4), root)
    pending = remaining_text(book, outputs=False)
    if pending:
        raise ValueError('English wording requires review: ' + json.dumps(pending[:10], ensure_ascii=False))
    nbformat.write(book, path)
    return book


if __name__ == '__main__':
    import sys
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
    print('ENGLISH_NOTEBOOK_SOURCE_COMPLETE')
