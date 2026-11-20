#!/usr/bin/env python3
"""Optimize the assembled Pages tree in place, before publishing."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import yaml

from optimize_layout import optimize_layout
from paginate_home import paginate_home

TOOLS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('public', type=Path, nargs='?', default=Path('public'))
    args = parser.parse_args()
    public = args.public.resolve()
    if not (public / 'index.html').is_file():
        parser.error(f'No site index in {public}')
    config = yaml.safe_load((TOOLS.parent / '_config.yml').read_text())
    per_page = config.get('index_generator', {}).get('per_page', config.get('per_page', 12))
    site_url = config['url'].rstrip('/')
    posts, pages = paginate_home(public, per_page, site_url)
    print(f'{posts} regular articles across {pages} index pages.', flush=True)
    optimize_layout(public, site_url)
    for script in ('optimize-post-images.py', 'optimize-runtime.py'):
        subprocess.run([sys.executable, str(TOOLS / script), str(public)], check=True)
    # A theme can render an article successfully while omitting its search metadata.
    expected = {p.parent.relative_to(public).as_posix() for p in
                public.glob('[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/**/index.html')}
    records = json.loads((public / 'js/search-index.json').read_text())
    indexed = {unquote(urlsplit(r['url']).path).strip('/') for r in records}
    missing = expected - indexed
    if missing:
        raise ValueError(f'Published articles missing from search: {sorted(missing)}')


if __name__ == '__main__':
    main()
