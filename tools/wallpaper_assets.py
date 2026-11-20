"""Prepare Shoka wallpaper renditions from a local checkout of wallpaperLibrary.

The checked-in WebPs were generated from Natsuneko3/wallpaperLibrary at
21cf22c60cb4818ae296234dfad08488a45975c2. Normal site builds use the
prepared images and do not download or re-encode the wallpaper library.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit
from pathlib import Path

from PIL import Image, ImageOps

ASSETS = Path(__file__).resolve().parent / 'appearance' / 'wallpapers'
WIDTHS = (480, 800, 1440)


def encode(source, directory):
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
    signature = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    variants = []
    for width in sorted(set(min(w, image.width) for w in WIDTHS)):
        height = max(1, round(image.height * width / image.width))
        filename = f'{signature}-{width}.webp'
        dest = directory / filename
        if not dest.exists():
            frame = image.resize((width, height), Image.Resampling.LANCZOS)
            frame.save(dest, 'WEBP', quality=76, method=4)
        variants.append([width, filename])
    return {'width': image.width, 'height': image.height, 'variants': variants}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('originals', type=Path)
    parser.add_argument('site', type=Path, help='Rendered site containing the authored wallpaper URLs')
    args = parser.parse_args()
    names = set()
    for page in args.site.rglob('*.html'):
        for url in re.findall(r'(?:src|data-background-image)="([^"]*wallpaperLibrary/[^"]*)"', page.read_text()):
            names.add(Path(unquote(urlsplit(url).path)).name)
    if not names:
        parser.error('No wallpaper references found')
    # The legacy HTML contains a misdecoded filename for this existing artwork.
    aliases = {'QQͼƬ20231119143925.jpg': 'QQ图片20231119143925.jpg'}
    names = sorted(names)
    sources = [args.originals / aliases.get(name, name) for name in names]
    ASSETS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = dict(zip(names, pool.map(lambda p: encode(p, ASSETS), sources)))
    used = {name for entry in entries.values() for _, name in entry['variants']}
    for stale in ASSETS.glob('*.webp'):
        if stale.name not in used:
            stale.unlink()
    (ASSETS / 'catalog.json').write_text(json.dumps(entries, ensure_ascii=False, sort_keys=True,
                                                   separators=(',', ':')) + '\n')
    print(f'Prepared {len(entries)} wallpapers')


if __name__ == '__main__':
    main()
