"""Assemble the published snapshot and render new/edited Hexo sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote

from bs4 import BeautifulSoup

from paginate_home import retired_page_html

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = "06755811f3d0bfb3441af5839c3833e5e40a9189"
SOURCE = "34cb411db058198cb22b236faef512fef616ef77"
ARTICLE = re.compile(r"^\d{4}/\d\d/\d\d/(.+)/index\.html$")
# Match only the two child slots of Shoka's published .post-nav component.
NAV = re.compile(
    r'(<div class="post-nav">\s*<div class="item left">)(.*?)(</div>\s*<div class="item right">)'
    r'(.*?)(</div>\s*</div>)', re.S
)
PUBLIC = ROOT / "public"
CONFIGS = ("_config.yml", "_config.shoka.yml")
# These settings describe the recovered snapshot, with pagination applied by
# optimize-site. A change to either file regenerates the configurable views.
SNAPSHOT_CONFIG = "e9fc249e2b13ada766eac47fcc7619bd71ff7483e988913c179e988370140ad7"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def ensure_commit(commit):
    if subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT,
                      stderr=subprocess.DEVNULL).returncode:
        git("fetch", "--no-tags", "--depth=1", "origin", commit)


def restore_snapshot(destination):
    # git archive handles the published tree independently of the working branch.
    with tempfile.TemporaryFile() as archive:
        subprocess.run(["git", "archive", PUBLISHED], cwd=ROOT, stdout=archive, check=True)
        archive.seek(0)
        subprocess.run(["tar", "-xf", "-", "-C", destination], stdin=archive, check=True)


def source_changes():
    tracked = git("diff", "--name-only", "-z", "--no-renames", SOURCE, "--", "source")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", "--", "source")
    return {Path(p.decode()) for p in (tracked + untracked).split(b"\0") if p}


def published_posts(snapshot):
    for path in sorted(snapshot.glob("[0-9][0-9][0-9][0-9]/*/*/**/index.html")):
        route = path.relative_to(snapshot).as_posix()
        if ARTICLE.fullmatch(route):
            yield route


def source_for(route):
    # The post's directory slug was corrected in the published edition.
    slug = ARTICLE.fullmatch(route).group(1)
    if slug == "图形学笔记/VirtualTexture":
        slug = "图形学笔记/Virtual Texture"
    return Path("source/_posts") / (slug + ".md")


def published_images(snapshot):
    covers = {}
    pinned = set()
    images = []
    for home in [snapshot / "index.html", *snapshot.glob("page/*/index.html")]:
        dom = BeautifulSoup(home.read_bytes(), "html.parser", from_encoding="utf-8")
        images.extend(li["data-background-image"] for li in dom.select("#imgs [data-background-image]"))
        for card in dom.select("article.item .cover a[href]"):
            route = unquote(card["href"]).strip("/") + "/index.html"
            img = card.select_one("img")
            if img and img.get("data-src"):
                covers[route] = img["data-src"]
            if card.find_parent(class_="sticky"):
                pinned.add(route)
    return covers, pinned, list(dict.fromkeys(images))


def restore_post(snapshot, route, target, covers, pinned, bodies):
    """Use the published text and metadata for indexes, and retain its original HTML."""
    dom = BeautifulSoup((snapshot / route).read_bytes(), "html.parser", from_encoding="utf-8")

    def meta(key):
        return dom.find("meta", property=key)["content"]

    fields = {
        "snapshot_route": route,
        "title": meta("og:title"),
        "date": meta("article:published_time"),
        "updated": meta("article:modified_time"),
        "permalink": route.removesuffix("index.html"),
        "categories": [e.get_text(strip=True) for e in dom.select(".breadcrumb [itemprop=name]")],
        "tags": [e["content"] for e in dom.find_all("meta", property="article:tag")],
    }
    if route in pinned:
        fields["sticky"] = True
    if route in covers:
        fields["cover"] = covers[route]
    header = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fields.items())
    body = dom.select_one("article [itemprop=articleBody]")
    if not body:
        raise ValueError(f"Missing published article body in {route}")
    # Hexo only needs these intermediate sources for its indexes and nav links.
    # Rendered pages for these routes are kept byte-for-byte until optimization.
    bodies[route] = body.decode_contents()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"---\n{header}\n---\n", encoding="utf-8")


def published_order(snapshot):
    successors = {}
    for route in published_posts(snapshot):
        nav = NAV.search((snapshot / route).read_text())
        if not nav:
            raise ValueError(f"Missing published post navigation in {route}")
        link = BeautifulSoup(nav[4], "html.parser").find("a")
        successors[route] = unquote(link["href"]).strip("/") + "/index.html" if link else None
    first, = set(successors) - set(successors.values())
    ranks = {}
    route = first
    while route:
        source = source_for(route).relative_to("source").as_posix()
        if source in ranks:
            raise ValueError(f"Cycle in published post navigation at {route}")
        ranks[source] = len(ranks)
        route = successors[route]
    if len(ranks) != len(successors):
        raise ValueError("Published previous/next links do not cover the full archive")
    return ranks


def update_navigation(old_path, new_path, preserve):
    old_page = old_path.read_text()
    old, new = NAV.search(old_page), NAV.search(new_path.read_text())
    if not old or not new:
        raise ValueError(f"Missing Shoka post navigation in {new_path}")

    def destination(slot):
        link = BeautifulSoup(slot, "html.parser").find("a")
        if not link:
            return None
        href = unquote(link["href"])
        if href.strip("/") + "/index.html" in preserve:
            return href
        return href, link.get_text(" ", strip=True), link.get("title")

    parts = list(old.groups())
    for slot in (2, 4):
        if destination(old[slot]) != destination(new[slot]):
            parts[slot - 1] = new[slot]
    navigation = "".join(parts)
    if navigation != old[0]:
        old_path.write_text(old_page[:old.start()] + navigation + old_page[old.end():])


def generate(stage, snapshot, changes):
    for name in ("package.json", "_config.yml", "_config.shoka.yml"):
        shutil.copy2(ROOT / name, stage / name)
    (stage / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
    (stage / "themes").mkdir()
    (stage / "themes/shoka").symlink_to(ROOT / "node_modules/hexo-theme-shoka", target_is_directory=True)
    shutil.copytree(ROOT / "source", stage / "source")
    covers, pinned, images = published_images(snapshot)
    image_list = stage / "source/_data/images.yml"
    if not image_list.exists():
        image_list.parent.mkdir(parents=True, exist_ok=True)
        image_list.write_text(json.dumps(images), encoding="utf-8")
    preserve = set()
    bodies = {}
    for route in published_posts(snapshot):
        source = source_for(route)
        if source in changes and (ROOT / source).exists():
            # Keep the legacy URL for the historically renamed source.
            if route.endswith("/图形学笔记/VirtualTexture/index.html"):
                md = stage / source
                text = md.read_text()
                if not re.search(r"^permalink:", text.split("---", 2)[1], re.M):
                    md.write_text(text.replace("---\n", "---\npermalink: " + route.removesuffix("index.html") + "\n", 1))
            continue
        preserve.add(route)
        restore_post(snapshot, route, stage / source, covers, pinned, bodies)
    if Path("source/about/index.md") not in changes:
        preserve.add("about/index.html")
    # The Markdown renderer never has to reparse pre-rendered HTML or code samples.
    (stage / "published-bodies.json").write_text(json.dumps(bodies, ensure_ascii=False))
    (stage / "scripts").mkdir()
    (stage / "published-order.json").write_text(json.dumps(published_order(snapshot)))
    shutil.copy2(ROOT / "tools/build-posts.js", stage / "scripts/build-posts.js")
    env = dict(os.environ, TZ="Asia/Shanghai")
    subprocess.run([ROOT / "node_modules/.bin/hexo", "generate", "--bail"], cwd=stage, env=env, check=True)
    # Only deliberately edited static source may replace a baseline asset.
    edited_assets = {
        hashlib.sha256((ROOT / path).read_bytes()).digest() for path in changes
        if (ROOT / path).is_file() and path.suffix.lower() != ".md"
    }
    rendered = stage / "public"
    if not (rendered / "index.html").is_file():
        raise RuntimeError("Hexo did not generate the home page")
    for old_page in snapshot.glob("page/*/index.html"):
        if old_page.parent.name.isdecimal() and not (rendered / old_page.relative_to(snapshot)).is_file():
            old_page.write_text(retired_page_html(), encoding="utf-8")
    for path in rendered.rglob("*"):
        if not path.is_file():
            continue
        name = path.relative_to(rendered).as_posix()
        output = snapshot / name
        if name in preserve:
            if ARTICLE.fullmatch(name):
                update_navigation(output, path, preserve)
            continue
        if output.exists() and path.suffix != ".html" and hashlib.sha256(path.read_bytes()).digest() not in edited_assets:
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        if name == "index.html" and Path("source/_data/images.yml") not in changes:
            # Shoka shuffles its gallery on every render. Preserve the published
            # first paint and rotation when editing unrelated posts.
            old_home = BeautifulSoup(output.read_bytes(), "html.parser", from_encoding="utf-8")
            new_home = BeautifulSoup(path.read_bytes(), "html.parser", from_encoding="utf-8")
            old_imgs, new_imgs = old_home.select_one("#imgs"), new_home.select_one("#imgs")
            if old_imgs and new_imgs:
                new_imgs.replace_with(old_imgs)
                output.write_text(str(new_home), encoding="utf-8")
                continue
        shutil.copy2(path, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PUBLIC)
    parser.add_argument("--skip-optimize", action="store_true", help="inspect the original Shoka markup")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination == ROOT or destination in ROOT.parents or args.output.is_symlink():
        parser.error("output must be a dedicated generated site directory")
    if destination.is_relative_to(ROOT / "source"):
        parser.error("output must be outside the source tree")
    if destination.exists() and destination != PUBLIC and any(destination.iterdir()):
        parser.error("custom output directory must be empty")
    ensure_commit(PUBLISHED)
    ensure_commit(SOURCE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".site-build-") as tmp:
        stage = Path(tmp)
        snapshot = stage / "published"
        snapshot.mkdir()
        restore_snapshot(snapshot)
        routes = {p.relative_to(snapshot) for p in snapshot.rglob("*.html")}
        changes = source_changes()
        settings = hashlib.sha256(b"\0".join((ROOT / path).read_bytes() for path in CONFIGS)).hexdigest()
        if changes or settings != SNAPSHOT_CONFIG:
            print("Rendering changed Hexo content or configuration", flush=True)
            generate(stage, snapshot, changes)
        if not args.skip_optimize:
            subprocess.run([sys.executable, ROOT / "tools/optimize-site.py", snapshot], cwd=ROOT, check=True)
        missing = sorted(str(r) for r in routes if not (snapshot / r).is_file())
        if missing:
            raise RuntimeError(f"Published routes missing from output: {missing}")
        (snapshot / ".nojekyll").touch()
        if destination.exists():
            destination.rename(stage / "previous-output")
        try:
            snapshot.rename(destination)
        except OSError:
            if (stage / "previous-output").exists():
                (stage / "previous-output").rename(destination)
            raise
        print(f"Built {destination}; retained all {len(routes)} historical HTML routes.")


if __name__ == "__main__":
    main()
