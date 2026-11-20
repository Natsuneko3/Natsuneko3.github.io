"""Generate responsive previews for local article images in a rendered Hexo site."""

import argparse
from functools import lru_cache
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from urllib.parse import quote, unquote, urlsplit

from PIL import Image, ImageOps, __version__ as PILLOW_VERSION, features


WIDTHS = (480, 800, 1280)
QUALITY = 83
METHOD = 4
RESAMPLING = Image.Resampling.LANCZOS
OUTPUT = Path("images/post-webp")
SIZES = "auto, (max-width: 991px) 100vw, (max-width: 1599px) 54rem, 70vw"
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
TOOLS = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("SHOKA_POST_IMAGES_CACHE") or
             TOOLS.parent / ".cache" / "shoka-post-images").expanduser().resolve()
RECIPE = (
    f"webp-v1:exif-transpose:keep-icc:{RESAMPLING.name}:q{QUALITY}:m{METHOD}:"
    f"pillow-{PILLOW_VERSION}:libwebp-{features.version('webp')}"
).encode()
LEGACY_PATHS = json.loads((TOOLS / "legacy-post-images.json").read_text(encoding="utf-8"))


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            tmp.write(data)
            tmp.close()
            temporary.chmod(0o644)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def recover_legacy_image(site, original):
    relative = original.relative_to(site)
    parent = relative.parent.as_posix()
    source = LEGACY_PATHS["source_directories"].get(parent)
    if source:
        saved = TOOLS.parent / source / relative.name
        if saved.is_file():
            atomic_write(original, saved.read_bytes())
            return original
    alias = LEGACY_PATHS["files"].get(relative.as_posix())
    if parent in LEGACY_PATHS["directories"]:
        alias = Path(LEGACY_PATHS["directories"][parent]) / relative.name
    if alias and (site / alias).is_file():
        return site / alias
    return None


@lru_cache(maxsize=None)
def previews(site, original):
    data = original.read_bytes()
    digest = sha256(RECIPE)
    digest.update(b"\0")
    digest.update(data)
    key = digest.hexdigest()
    with Image.open(BytesIO(data)) as image:
        if getattr(image, "is_animated", False):
            return None
        width, height = image.size
        if image.getexif().get(274) in (5, 6, 7, 8):
            width, height = height, width
        variants = []
        oriented = None
        for target in sorted({min(width, w) for w in WIDTHS}):
            file = site / OUTPUT / f"{key}-{target}.webp"
            cached = CACHE / file.name
            if not cached.is_file():
                if oriented is None:
                    oriented = ImageOps.exif_transpose(image)
                scaled = oriented.copy()
                scaled.thumbnail((target, oriented.height), RESAMPLING)
                encoded = BytesIO()
                scaled.save(encoded, format="WEBP", quality=QUALITY, method=METHOD,
                            icc_profile=image.info.get("icc_profile") or b"")
                atomic_write(cached, encoded.getvalue())
            if not file.is_file():
                atomic_write(file, cached.read_bytes())
            variants.append((file, target))
        return width, height, variants


class ArticleImages(HTMLParser):
    def __init__(self, site, page, source):
        super().__init__(convert_charrefs=False)
        self.site = site
        self.page = page
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer("\n", source)]
        self.stack = []
        self.body_depth = None
        self.edits = []
        self.missing = set()
        self.repaired = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img" and self.body_depth is not None and "picture" not in self.stack:
            self.replace_image(attributes)
        if tag not in VOID:
            self.stack.append(tag)
            if "articleBody" in (attributes.get("itemprop") or "").split():
                self.body_depth = len(self.stack)

    def handle_endtag(self, tag):
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag):]
            if self.body_depth is not None and len(self.stack) < self.body_depth:
                self.body_depth = None

    def replace_image(self, attrs):
        url = attrs.get("data-src") or attrs.get("src")
        if (not url or attrs.get("data-srcset")
                or (attrs.get("srcset") and "images/post-webp/" not in attrs["srcset"])):
            return
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            return
        path = unquote(parts.path)
        original = (self.site / path.lstrip("/") if path.startswith("/")
                    else self.page.parent / path).resolve()
        if not original.is_relative_to(self.site) or original.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            return
        if not original.is_file():
            recovered = recover_legacy_image(self.site, original)
            if recovered is None:
                self.missing.add(original.relative_to(self.site))
                return
            original = recovered
            repaired_path = Path(os.path.relpath(original, self.page.parent)).as_posix()
            url = parts._replace(path=quote(repaired_path)).geturl()
            self.repaired += 1
        result = previews(self.site, original)
        if not result:
            return
        width, height, variants = result
        # Shoka wraps the image at runtime and takes its lightbox URL from src.
        # Native srcset controls the preview, including on PJAX navigations.
        attrs.pop("data-src", None)
        attrs["src"] = url
        attrs["srcset"] = ", ".join(
            f"{Path(os.path.relpath(file, self.page.parent)).as_posix()} {target}w"
            for file, target in variants
        )
        attrs.setdefault("sizes", SIZES)
        if not attrs.get("width") and not attrs.get("height"):
            attrs.update(width=str(width), height=str(height))
            style = (attrs.get("style") or "").rstrip("; ")
            if not re.search(r"(?:^|;)\s*height\s*:", style, re.I):
                attrs["style"] = (style + "; " if style else "") + "height: auto"
        attrs.setdefault("loading", "lazy")
        attrs.setdefault("decoding", "async")
        tag = "<img" + "".join(
            f' {name}="{escape(value, quote=True)}"' if value is not None else f" {name}"
            for name, value in attrs.items()
        ) + ">"
        line, column = self.getpos()
        start = self.lines[line - 1] + column
        previous = self.get_starttag_text()
        if tag != previous:
            self.edits.append((start, start + len(previous), tag))

    def save(self):
        fragments = []
        cursor = 0
        for start, end, tag in self.edits:
            fragments.extend((self.source[cursor:start], tag))
            cursor = end
        fragments.append(self.source[cursor:])
        atomic_write(self.page, "".join(fragments).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_dir", nargs="?", default="public", type=Path)
    site = parser.parse_args().public_dir.resolve()
    if not (site / "index.html").is_file():
        parser.error(f"{site} does not contain a rendered index.html")
    pages = images = repaired = 0
    missing = set()
    for page in site.rglob("*.html"):
        source = page.read_bytes().decode("utf-8")
        if "articleBody" not in source:
            continue
        document = ArticleImages(site, page, source)
        document.feed(source)
        document.close()
        missing.update(document.missing)
        repaired += document.repaired
        if document.edits:
            document.save()
            pages += 1
            images += len(document.edits)
    print(f"Updated {images} article images on {pages} pages. Repaired {repaired} links. "
          f"Missing local originals: {len(missing)}.")


if __name__ == "__main__":
    main()
