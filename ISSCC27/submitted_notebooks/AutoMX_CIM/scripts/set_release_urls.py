"""Record public release URLs locally after the owner uploads both prepared assets."""
from pathlib import Path
import argparse
import json
from urllib.parse import urlparse, quote

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-url', required=True,
                        help='https://github.com/OWNER/REPO/releases/download/TAG')
    args = parser.parse_args()
    base = args.release_url.rstrip('/')
    parsed = urlparse(base)
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or len(parts) != 5 or parts[2:4] != ['releases', 'download']:
        parser.error('Supply an HTTPS github.com/OWNER/REPO/releases/download/TAG URL.')
    root = Path(__file__).resolve().parents[1]
    path = root / 'runtime_assets.json'
    assets = json.loads(path.read_text())
    rows = []
    for key in ['runtime', 'measurement_records']:
        item = assets[key]
        item['download_url'] = base + '/' + quote(item['filename'])
        rows.append(f"- [{item['filename']}]({item['download_url']}) — {item['required_for']}.")
    assets['status'] = 'PUBLIC_URLS_CONFIGURED_DOWNLOAD_AVAILABILITY_NOT_TESTED'
    assets['publication_note'] = 'Public URLs configured locally; verify unauthenticated downloads before opening the PR.'
    path.write_text(json.dumps(assets, indent=2) + '\n')
    (root / 'RELEASE_ASSETS.md').write_text('# Reproduction release assets\n\n' + '\n'.join(rows) +
        '\n\nRestore the runtime archive using `python scripts/restore_runtime.py --archive PATH`. '
        'See [reproduction instructions](docs/REPRODUCIBILITY.md) for tool requirements.\n')
    print('Release URLs recorded. Verify that both downloads are public before submitting.')

if __name__ == '__main__':
    main()
