// Template contents stay inert until the next slide is needed.
(() => {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let stop = () => {};

  function start() {
    stop();
    const host = document.querySelector('#imgs .site-slides');
    if (!host || document.hidden || reducedMotion.matches || navigator.connection?.saveData) return;
    const slides = [...host.querySelectorAll('template')];
    if (slides.length < 2) return;

    let active = true;
    let timer;
    let current = host.querySelector('img[data-active]') || host.querySelector('img');
    current.dataset.active = '';
    let index = Number(current.dataset.slide || 0);
    let pending;
    stop = () => {
      active = false;
      clearTimeout(timer);
      pending?.remove();
    };

    async function prepareNext() {
      const nextIndex = (index + 1) % slides.length;
      const node = slides[nextIndex].content.firstElementChild.cloneNode(true);
      node.className = 'incoming';
      node.dataset.slide = nextIndex;
      node.fetchPriority = 'low';
      pending = node;
      const earliestSwitch = performance.now() + 1000;
      host.append(node);
      try {
        await node.decode();
      } catch {
        node.remove();
        if (active) {
          index = nextIndex;
          timer = setTimeout(prepareNext, 5000);
        }
        return;
      }
      if (!active || !host.isConnected) return;
      timer = setTimeout(() => {
        node.classList.remove('incoming');
        node.dataset.active = '';
        const previous = current;
        delete previous.dataset.active;
        current = node;
        pending = undefined;
        index = nextIndex;
        // Keep the previous image behind the incoming one during the crossfade.
        setTimeout(() => previous.remove(), 460);
        timer = setTimeout(prepareNext, 5000);
      }, Math.max(0, earliestSwitch - performance.now()));
    }
    timer = setTimeout(prepareNext, 5000);
  }

  start();
  window.addEventListener('pjax:success', start);
  window.addEventListener('pageshow', event => { if (event.persisted) start(); });
  window.addEventListener('pagehide', () => stop());
  document.addEventListener('visibilitychange', start);
  reducedMotion.addEventListener('change', start);
})();
