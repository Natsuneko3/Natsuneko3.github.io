"""Repaginate Shoka's existing cards without rendering or truncating article text."""
import re

from bs4 import BeautifulSoup



RETIRED = '<!-- retired home page -->'


def retired_page_html():
    return (f'<!doctype html>{RETIRED}<html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta http-equiv="refresh" content="0;url=/"><link rel="canonical" href="/">'
            '<title>文章列表</title></head><body><a href="/">返回文章列表</a></body></html>\n')


def page_url(number):
    return '/' if number == 1 else f'/page/{number}/'


def navigation(soup, number, total):
    nav = soup.new_tag('nav', attrs={'class': 'pagination', 'aria-label': '文章列表分页'})
    inner = soup.new_tag('div', attrs={'class': 'inner'})
    nav.append(inner)

    def add_arrow(target, direction, label):
        anchor = soup.new_tag('a', href=page_url(target), rel=direction,
                              attrs={'class': f'extend {direction}', 'aria-label': label})
        side = 'left' if direction == 'prev' else 'right'
        anchor.append(soup.new_tag('i', attrs={'class': f'ic i-angle-{side}', 'aria-hidden': 'true'}))
        inner.append(anchor)

    if number > 1:
        add_arrow(number - 1, 'prev', '上一页')
    for target in range(1, total + 1):
        if target == number:
            item = soup.new_tag('span', attrs={'class': 'page-number current', 'aria-current': 'page'})
        else:
            item = soup.new_tag('a', href=page_url(target), attrs={'class': 'page-number'})
        item.string = str(target)
        inner.append(item)
    if number < total:
        add_arrow(number + 1, 'next', '下一页')
    return nav


def paginate_home(public, per_page, site_url):
    paths = [public / 'index.html']
    paths += sorted((p for p in (public / 'page').glob('*/index.html') if p.parent.name.isdigit()),
                    key=lambda p: int(p.parent.name))
    documents = [(path, path.read_text()) for path in paths]
    # After a page-size change an old numbered URL may be a permanent redirect.
    # It has no cards and can become a real page again if the blog grows.
    active = [(path, html) for path, html in documents if RETIRED not in html]
    if not active or active[0][0] != public / 'index.html':
        raise ValueError('The root article list is missing')
    templates = [html for _, html in active]
    cards = []
    existing_sizes = []
    already_paginated = True
    for path, html in active:
        soup = BeautifulSoup(html, 'html.parser')
        posts = soup.select_one('#main .segments.posts')
        if posts is None:
            raise ValueError(f'Missing article list in {path}')
        page_cards = posts.find_all('article', recursive=False)
        existing_sizes.append(len(page_cards))
        canonical = soup.select_one('link[rel=canonical]')
        already_paginated &= (posts.get('data-per-page') == str(per_page) and canonical is not None
                              and canonical.get('href') == site_url + page_url(len(existing_sizes)))
        cards.extend(page_cards)
    targets = [a.select_one('.cover a, h3 a')['href'] for a in cards]
    if len(targets) != len(set(targets)):
        raise ValueError('Home pagination contains duplicate article URLs')
    requested_size = per_page
    if per_page == 0:
        per_page = max(1, len(cards))
    total = max(1, (len(cards) + per_page - 1) // per_page)

    expected_sizes = [min(per_page, len(cards) - i * per_page) for i in range(total)]
    if already_paginated and existing_sizes == expected_sizes:
        return len(cards), total

    for number in range(1, total + 1):
        soup = BeautifulSoup(templates[min(number, len(templates)) - 1], 'html.parser')
        posts = soup.select_one('#main .segments.posts')
        posts.clear()
        posts['data-per-page'] = str(requested_size)
        for card in cards[(number - 1) * per_page:number * per_page]:
            posts.append(card.extract())
        if number > 1:
            sticky = soup.select_one('#main .segments.sticky')
            if sticky:
                heading = sticky.find_previous_sibling('h2')
                if heading:
                    heading.decompose()
                sticky.decompose()

        nav = soup.select_one('#main nav.pagination')
        if nav:
            nav.decompose()
        if total > 1:
            soup.select_one('#main').append(navigation(soup, number, total))
        url = page_url(number)
        for tag in soup.select('link[rel=canonical]'):
            tag['href'] = site_url + url
        for tag in soup.select('meta[property="og:url"]'):
            tag['content'] = site_url + url
        for script in soup.select('script[data-config]'):
            if script.string:
                script.string = re.sub(r'(\bpath\s*:\s*)(["\']).*?\2',
                                       lambda m: m[1] + '"' + url.lstrip('/') + '"', script.string, count=1)
        path = public / url.strip('/') / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(soup))
    for stale in paths[1:]:
        if int(stale.parent.name) > total:
            stale.write_text(retired_page_html())
    return len(cards), total
