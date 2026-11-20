"""Apply local responsive artwork and progressive slideshow loading to Shoka HTML."""
from hashlib import sha256
from html import escape, unescape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from wallpaper_assets import ASSETS, encode

PUBLIC_MEDIA = '/media/wallpapers/'
# These old third-party covers deny image delivery. Keep the authored URL in
# Markdown and use a bundled wallpaper in its slot until it can be imported.
UNAVAILABLE = {
    'wallhaven-e72x6k.jpg', 'wallhaven-z8lmpo.jpg', 'wallhaven-yxj26x.jpg',
    'wallhaven-k752qd.jpg', 'wallhaven-o3er65.jpg', 'wallhaven-q6wmkq.jpg',
    'v2-147be5e9a1831e26487605bfee955919_1440w.jpg',
    'v2-79bce61997eaf687cca50c7dabcb3065_1440w.jpg',
    'v2-fa0f656bfc72e1635473a5a545572c73_1440w.jpg',
}
HERO = re.compile(r'<div\b(?=[^>]*\bid=["\']imgs["\'])[^>]*>\s*(<ul\b.*?</ul>|<img\b[^>]*?/?>)\s*</div>', re.S | re.I)
COVER = re.compile(r'(<div class="cover">\s*<a\b[^>]*>\s*)(<img\b[^>]*>)', re.I)
BACKGROUND = re.compile(r'\bdata-background-image="([^"]+)"')


class ArtLibrary:
    def __init__(self, public):
        self.public = public.resolve()
        self.destination = self.public / PUBLIC_MEDIA.strip('/')
        self.destination.mkdir(parents=True, exist_ok=True)
        self.entries = json.loads((ASSETS / 'catalog.json').read_text())
        self.local = {}
        self.substituted = set()
        self.defaults = [self.entries['wallhaven-' + slug + '.jpg'] for slug in
                         ('857grj', '4gyvl3', 'o523z9', 'lmel6p', 'x89783', 'x8998d')]

    def resolve(self, url, page):
        parts = urlsplit(unescape(url))
        path = Path(unquote(parts.path))
        if not parts.netloc:
            original = ((self.public / str(path).lstrip('/')) if path.is_absolute() else page.parent / path).resolve()
            if (original.is_relative_to(self.public) and original.is_file()
                    and original.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}):
                if original not in self.local:
                    self.local[original] = encode(original, self.destination)
                return self.local[original]
            return None

        owned = ('/Natsuneko3/wallpaperLibrary/' in parts.path and
                 parts.hostname in {'github.com', 'raw.githubusercontent.com', 'cdn.jsdelivr.net'})
        if owned:
            return self.entries.get(path.name)
        if parts.hostname in {'w.wallhaven.cc', 'pic1.zhimg.com', 'pica.zhimg.com', 'picx.zhimg.com'} and path.name in UNAVAILABLE:
            if path.name in self.entries:
                return self.entries[path.name]
            self.substituted.add(url)
            return self.defaults[int.from_bytes(sha256(url.encode()).digest()[:2], 'big') % len(self.defaults)]
        return None

    def url(self, filename):
        dest = self.destination / filename
        if not dest.exists():
            shutil.copyfile(ASSETS / filename, dest)
        return PUBLIC_MEDIA + filename

    def image(self, source, page, *, card=False, priority=False):
        entry = self.resolve(source, page)
        attrs = {'alt': '', 'decoding': 'async'}
        if card:
            attrs['loading'] = 'lazy'
        if priority:
            attrs['fetchpriority'] = 'high'
        if entry:
            variants = entry['variants']
            if card:
                variants = variants[:2]
            attrs.update(width=entry['width'], height=entry['height'],
                         srcset=', '.join(f'{self.url(name)} {w}w' for w, name in variants),
                         sizes='(max-width: 767px) 100vw, 420px' if card else '100vw',
                         src=self.url(variants[0][1]))
        else:
            attrs['src'] = source
        return '<img ' + ' '.join(f'{k}="{escape(str(v), quote=True)}"' for k, v in attrs.items()) + '>'

    def hero(self, match, page):
        fragment = BeautifulSoup(match[1], 'html.parser')
        urls = [el.get('data-background-image') for el in fragment.select('li[data-background-image]')]
        if not urls:
            img = fragment.find('img')
            if img:
                urls = [img.get('data-src') or img.get('src')]
        if not all(urls) or not urls:
            return match[0]
        first = self.image(urls[0], page, priority=True)
        # Each template is inert; the browser can discover just the first image.
        slides = ''.join('<template>' + self.image(url, page) + '</template>' for url in urls) if len(urls) > 1 else ''
        return '<div id="imgs" class="pjax"><div class="site-slides">' + first + slides + '</div></div>'

    def card(self, match, page):
        img = BeautifulSoup(match[2], 'html.parser').img
        url = img.get('data-src') or img.get('src')
        if not url or 'srcset' in img.attrs:
            return match[0]
        return match[1] + self.image(url, page, card=True)

    def background(self, match, page):
        url = unescape(match[1])
        if url.startswith(PUBLIC_MEDIA):
            return match[0]
        entry = self.resolve(url, page)
        if entry:
            url = self.url(entry['variants'][0][1])
            return f'data-background-image="{url}"'
        return match[0]


def optimize_layout(public, site_url):
    library = ArtLibrary(public)
    count = 0
    for page in public.rglob('*.html'):
        original = page.read_text()
        if 'id="imgs"' not in original and "id='imgs'" not in original:
            continue
        html = HERO.sub(lambda m: library.hero(m, page), original, count=1)
        # Other legacy pages still carry the example domain in generated metadata.
        head, separator, body = html.partition('</head>')
        head = re.sub(r'((?:href|content)=")https?://example\.com(?=/)', lambda m: m[1] + site_url, head)
        html = head + separator + body
        html = COVER.sub(lambda m: library.card(m, page), html)
        html = BACKGROUND.sub(lambda m: library.background(m, page), html)
        if html != original:
            page.write_text(html)
            count += 1
    print(f'Updated artwork on {count} pages; {len(library.substituted)} unavailable cover URLs used a local fallback.')
