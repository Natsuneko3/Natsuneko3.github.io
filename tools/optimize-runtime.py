#!/usr/bin/env python3
"""Update a generated Shoka 0.2.5 site using the checked-in runtime libraries."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote

RESOURCES = Path(__file__).resolve().parent / "runtime"
APPEARANCE = RESOURCES.parent / "appearance"
APP_MARKER = "/* local Shoka runtime */"
CSS_MARKER = "/* local search dialog */"
BUNDLE = "shoka-core.js"
ICON_FONT = "font_1832207_igi8uaupcus.woff2"
# Files in vendor/ are the unchanged UMD distributions and licenses from the
# matching npm package versions. Native fetch replaces Shoka's fetch polyfill.
LIBRARIES = (
    ("pace-js-1.0.2", "pace.min.js"),
    ("pjax-0.2.8", "pjax.min.js"),
    ("animejs-3.2.0", "anime.min.js"),
    ("lozad-1.16.0", "lozad.min.js"),
    ("quicklink-2.3.0", "quicklink.umd.js"),
)
GOOGLE_FONTS = re.compile(r'<link\b[^>]*\bhref="(?:https?:)?//fonts\.googleapis\.com/[^"]*"[^>]*>')
POLYFILL = '<script src="https://cdn.polyfill.io/v2/polyfill.js"></script>'
CORE_TAG = re.compile(r'<script\b[^>]*\bsrc="(?:(?:https?:)?//cdn\.jsdelivr\.net/combine/npm/pace-js@[^"]+|/js/shoka-core\.js(?:\?[^"]*)?)"[^>]*></script>')
APP_TAG = re.compile(r'<script\b[^>]*\bsrc="/js/app\.js(?:\?[^"]*)?"[^>]*></script>')
STYLE_TAG = re.compile(r'href="/css/app\.css(?:\?[^"]*)?"')


def version(data):
    return hashlib.sha256(data.encode()).hexdigest()[:12]


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected one Shoka 0.2.5 occurrence of {before[:64]!r}")
    return text.replace(before, after)


class Article(HTMLParser):
    """Read visible post text, preserving code tokens split by syntax highlighting."""

    VOID = set("area base br col embed hr img input link meta param source track wbr".split())
    BREAK = set("p div h1 h2 h3 h4 h5 h6 pre li tr td section blockquote".split())

    def __init__(self):
        super().__init__()
        self.is_post = False
        self.title = ""
        self.headline = []
        self.in_headline = False
        self.in_body = False
        self.nodes = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1" and "headline" in (attrs.get("itemprop") or "").split():
            self.in_headline = True
        if tag == "meta":
            if attrs.get("property") == "og:type":
                self.is_post = attrs.get("content") == "article"
            if attrs.get("property") == "og:title":
                self.title = attrs.get("content", "")
        if not self.in_body and attrs.get("itemprop") != "articleBody":
            return
        self.in_body = True
        hidden = bool(self.nodes and self.nodes[-1][1]) or (
            tag in {"script", "style", "noscript"} or attrs.get("aria-hidden") == "true" or
            bool({"anchor", "gutter"} & set((attrs.get("class") or "").split()))
        )
        if (tag in self.BREAK or tag == "br") and not hidden:
            self.parts.append(" ")
        if tag not in self.VOID:
            self.nodes.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_headline = False
        if not self.in_body or tag in self.VOID:
            return
        for pos in range(len(self.nodes) - 1, -1, -1):
            if self.nodes[pos][0] == tag:
                if tag in self.BREAK and not self.nodes[pos][1]:
                    self.parts.append(" ")
                del self.nodes[pos:]
                self.in_body = bool(self.nodes)
                break

    def handle_data(self, data):
        if self.in_headline:
            self.headline.append(data)
        if self.nodes and not self.nodes[-1][1]:
            self.parts.append(data)


def search_record(path, html):
    if 'itemprop="articleBody"' not in html:
        return None
    post = Article()
    post.feed(html)
    post.close()
    body = " ".join("".join(post.parts).split())
    title = post.title or " ".join("".join(post.headline).split())
    dated_post = re.match(r"^\d{4}/\d{2}/\d{2}/.+/index\.html$", path.as_posix())
    if not (post.is_post or dated_post) or not title or not body:
        return None
    url = "/" + quote(path.as_posix())
    return {"title": title, "url": url.removesuffix("index.html"), "body": body}


def patch_app(app):
    # Native links work immediately, even if the optional gallery CDN is offline.
    if "ShokaRuntime.linkOriginalImages" not in app:
        gallery_start = app.index('u.each(e+" .md img:not(.emoji):not(.vemoji)",')
        gallery_end = app.index('u.each(e+" div.gallery",', gallery_start)
        app = app[:gallery_start] + app[gallery_end:]
        app = replace_once(app, 'if(u(e+" .md img")){s("fancybox")',
                           'if(LOCAL.fancybox&&u(e+" .md img")){ShokaRuntime.linkOriginalImages(e);s("fancybox")')
        app = replace_once(app, 'new Pjax({selectors:',
                           'new Pjax({elements:"a[href]:not(.fancybox), form[action]",selectors:')
    if app.startswith(APP_MARKER):
        return app
    # These narrow anchors are deliberately specific to the generated theme.
    # Stop on a different release before publishing a partially patched script.
    start = app.index("const me=function(t){if(e.search===null)return;")
    end = app.index("const ve=function()", start)
    app = app[:start] + "const me=ShokaRuntime.installSearch;" + app[end:]
    app = re.sub(r'\bsearch:\{appID:"[^"]*",apiKey:"[^"]*",indexName:"[^"]*",hits:\{per_page:\d+\}\},', "", app, count=1)
    app = replace_once(app, 'r("valine",function(){var t=', 'ShokaRuntime.onCommentsVisible(function(container){r("valine",function(){if(!container.isConnected)return;var t=')
    app = replace_once(app, '},window.MiniValine);if(!t)', '},window.MiniValine)});if(!t)')
    app = replace_once(app, 'lozad("img, [data-background-image]"',
                       'lozad("img[data-src], img[data-srcset], [data-background-image]"')
    # One timeline per click. The shared clear loop runs while any is active.
    app = replace_once(app, 'anime.timeline().add({targets:n,x:function(e){return e.endPos.x}',
        'activeBursts++;anime.timeline({complete:function(){if(--activeBursts===0){qe.pause();Ce.clearRect(0,0,we.width,we.height)}}}).add({targets:n,x:function(e){return e.endPos.x}')
    app = replace_once(app, 'var qe=anime({duration:Infinity,update:', 'var activeBursts=0;var qe=anime({autoplay:false,duration:Infinity,update:')
    app = replace_once(app, 'function(e){qe.play();Ne(e);Ae(ke,Le)}',
        'function(e){if(matchMedia("(prefers-reduced-motion: reduce)").matches)return;qe.play();Ne(e);Ae(ke,Le)}')
    return APP_MARKER + "\n" + app


def patch_css(css):
    css = css.split(CSS_MARKER)[0].rstrip()
    css = re.sub(r"@font-face\{font-family:ic;[^}]+\}",
                 f'@font-face{{font-family:ic;src:url("/fonts/{ICON_FONT}") format("woff2");font-display:swap}}',
                 css, count=1)
    css = re.sub(r"(?:'Fredericka the Great',)?Mulish,(?:'Noto Serif (?:SC|JP)',)*"
                 r'(?:Mulish,)?-apple-system,"PingFang SC","Microsoft YaHei",sans-serif',
                 'system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif', css)
    css = css.replace('Inconsolata,consolas,Menlo,-apple-system,"PingFang SC","Microsoft YaHei"',
                      'ui-monospace,SFMono-Regular,Consolas,Menlo,monospace')
    return css + "\n" + CSS_MARKER + "\n" + (RESOURCES / "site.css").read_text() + (APPEARANCE / "slideshow.css").read_text()


def build_core(index_version):
    chunks = []
    notices = []
    for name, script in LIBRARIES:
        directory = RESOURCES / "vendor" / name
        chunks.append((directory / script).read_text())
        license_file = next(directory.glob("LICENSE*"))
        notices.append(name + "\n" + license_file.read_text())
    chunks.append((RESOURCES / "site.js").read_text().replace("__SEARCH_INDEX_VERSION__", index_version))
    chunks.append((APPEARANCE / "slideshow.js").read_text())
    notices.append((RESOURCES / "vendor/shoka-iconfont/SOURCE.txt").read_text())
    return "\n;\n".join(chunks), "\n\n".join(notices)


def write_if_changed(path, content):
    data = content.encode()
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def optimize(public):
    app_path = public / "js/app.js"
    style_path = public / "css/app.css"
    app = patch_app(app_path.read_text())
    style = patch_css(style_path.read_text())
    pages = []
    records = []
    for path in sorted(public.rglob("*.html")):
        html = path.read_text()
        if not APP_TAG.search(html):
            continue
        record = search_record(path.relative_to(public), html)
        if record:
            records.append(record)
        if len(CORE_TAG.findall(html)) != 1 or len(APP_TAG.findall(html)) != 1:
            raise ValueError(f"Unrecognized Shoka script tags in {path}")
        pages.append((path, html))
    if not pages or not records:
        raise ValueError("No Shoka pages or searchable posts found")

    index = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    core, notices = build_core(version(index))
    core_tag = f'<script defer src="/js/{BUNDLE}?v={version(core)}"></script>'
    app_tag = f'<script defer src="/js/app.js?v={version(app)}"></script>'
    style_url = f'href="/css/app.css?v={version(style)}"'
    for path, html in pages:
        html = GOOGLE_FONTS.sub("", html).replace(POLYFILL, "")
        html = CORE_TAG.sub(core_tag, html)
        html = APP_TAG.sub(app_tag, html)
        html = STYLE_TAG.sub(style_url, html)
        html = re.sub(r'<li class="item search">\s*<i class="ic i-search"></i>\s*</li>',
            '<li class="item search" role="button" tabindex="0" aria-label="搜索文章"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="7"/><path d="m15 15 7 7"/></svg></li>', html)
        write_if_changed(path, html)

    font_path = public / "fonts" / ICON_FONT
    font_path.parent.mkdir(exist_ok=True)
    font_data = (RESOURCES / "vendor/shoka-iconfont" / ICON_FONT).read_bytes()
    if not font_path.exists() or font_path.read_bytes() != font_data:
        font_path.write_bytes(font_data)
    for path, content in ((app_path, app), (style_path, style), (public / "js" / BUNDLE, core),
                          (public / "js/search-index.json", index), (public / "js/THIRD-PARTY.txt", notices)):
        write_if_changed(path, content)
    print(f"Updated {len(pages)} Shoka pages; indexed {len(records)} full articles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public", type=Path, nargs="?", default=Path("public"))
    optimize(parser.parse_args().public)
