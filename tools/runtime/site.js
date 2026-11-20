// Extensions for the published Shoka 0.2.5 theme.
window.ShokaRuntime = (() => {
  let commentObserver;
  function onCommentsVisible(start) {
    commentObserver?.disconnect();
    const container = document.querySelector("#comments");
    if (!container) return;
    commentObserver = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting) && container.isConnected) {
        commentObserver.disconnect();
        start(container);
      }
    }, { rootMargin: "300px" });
    commentObserver.observe(container);
  }

  function linkOriginalImages(scope) {
    for (const image of document.querySelectorAll(scope + " .md img:not(.emoji):not(.vemoji)")) {
      if (image.closest("a")) continue;
      const original = image.dataset.src || image.getAttribute("src");
      if (!original) continue;
      const link = document.createElement("a");
      link.href = original;
      link.className = "fancybox";
      link.setAttribute("itemscope", "");
      link.setAttribute("itemtype", "http://schema.org/ImageObject");
      link.setAttribute("itemprop", "url");
      const gallery = image.closest(".gallery");
      if (!gallery) {
        link.dataset.fancybox = "default";
        link.rel = "default";
      }
      const preview = image.closest("picture") || image;
      preview.replaceWith(link);
      link.append(preview);
      if (image.title) {
        link.dataset.caption = image.title;
        const caption = document.createElement("span");
        caption.className = gallery ? "jg-caption" : "image-info";
        caption.textContent = image.title;
        link.append(caption);
      }
    }
  }

  function installSearch() {
    const dialog = document.createElement("dialog");
    dialog.id = "search";
    dialog.setAttribute("aria-label", "文章搜索");
    dialog.innerHTML = `<div class="inner">
      <div class="header">
        <div class="search-input-container"><input type="search" class="search-input" aria-label="搜索文章" placeholder="搜索文章标题或正文"></div>
        <button type="button" class="close-btn" aria-label="关闭搜索">×</button>
      </div>
      <div class="results"><div class="inner">
        <div role="status" aria-live="polite"></div>
        <button type="button" class="retry" hidden>重新加载</button>
        <div id="search-hits"><ol></ol></div>
      </div></div>
    </div>`;
    document.body.append(dialog);
    const input = dialog.querySelector("input");
    const results = dialog.querySelector("ol");
    const status = dialog.querySelector("[role=status]");
    const retry = dialog.querySelector(".retry");
    let articles;
    let loading;
    let opener;

    function render() {
      results.replaceChildren();
      if (!articles) return;
      const query = input.value.trim().normalize("NFKC").toLowerCase();
      if (!query) {
        status.textContent = "";
        return;
      }
      const words = query.split(/\s+/);
      const matches = articles.filter(article =>
        words.every(word => article.heading.includes(word) || article.text.includes(word))
      );
      const score = a => (a.heading === query ? 10 : 0) +
        (a.heading.includes(query) ? 3 : 0) +
        words.filter(word => a.heading.includes(word)).length;
      matches.sort((a, b) => score(b) - score(a));
      const items = document.createDocumentFragment();
      for (const article of matches) {
        const li = document.createElement("li");
        li.className = "item";
        const link = document.createElement("a");
        link.href = article.url;
        link.textContent = article.title;
        li.append(link);
        items.append(li);
      }
      results.append(items);
      status.textContent = matches.length ? `找到 ${matches.length} 篇文章` : "没有找到匹配的文章";
      results.parentElement.scrollTop = 0;
    }

    async function loadIndex() {
      if (articles || loading) return;
      loading = true;
      retry.hidden = true;
      status.textContent = "正在加载文章索引…";
      try {
        const response = await fetch("/js/search-index.json?v=__SEARCH_INDEX_VERSION__");
        if (!response.ok) throw new Error(String(response.status));
        const data = await response.json();
        articles = data.map(({ title, url, body }) => ({
          title, url, heading: title.normalize("NFKC").toLowerCase(),
          text: body.normalize("NFKC").toLowerCase()
        }));
        render();
      } catch {
        status.textContent = "文章索引加载失败";
        retry.hidden = false;
      } finally {
        loading = false;
      }
    }

    function open(button) {
      if (dialog.open) return;
      opener = button;
      dialog.showModal();
      input.focus();
      loadIndex();
    }

    input.addEventListener("input", render);
    retry.addEventListener("click", loadIndex);
    dialog.querySelector(".close-btn").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", event => {
      if (event.target === dialog || event.target.closest("#search-hits a")) dialog.close();
    });
    dialog.addEventListener("close", () => opener?.focus({ preventScroll: true }));
    document.addEventListener("click", event => {
      const button = event.target.closest("#nav .search");
      if (button) open(button);
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && dialog.open) {
        event.preventDefault();
        dialog.close();
        return;
      }
      const button = event.target.closest("#nav .search");
      if (button && ["Enter", " "].includes(event.key)) {
        event.preventDefault();
        open(button);
      }
    });
    window.addEventListener("pjax:send", () => { if (dialog.open) dialog.close(); });
  }

  return { installSearch, onCommentsVisible, linkOriginalImages };
})();
