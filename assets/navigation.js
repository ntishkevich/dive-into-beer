function initNavigation() {
  const root = document.documentElement;
  const nav = document.querySelector('.topnav');
  const main = document.querySelector('#atlas-content');
  const title = nav.querySelector('[data-current-section-title]');
  const menu = nav.querySelector('.header-index');
  const progress = CSS.supports('animation-timeline', 'scroll(root block)')
    ? null
    : nav.querySelector('.reading-progress span');
  const sections = [...main.querySelectorAll('.sheet[data-nav-group]')];
  const linksByGroup = new Map();

  for (const link of document.querySelectorAll('[data-section-link]')) {
    const group = link.dataset.sectionLink;
    if (!linksByGroup.has(group)) linksByGroup.set(group, []);
    linksByGroup.get(group).push(link);
  }

  let offsets = [];
  let headerHeight = 0;
  let headerGap = 0;
  let scrollRange = 1;
  let layoutChanged = false;
  let frame = 0;
  let current;
  let initialTarget;

  function update() {
    frame = 0;
    let scrollTop = window.scrollY;
    let measuredHeight = headerHeight;
    let targetTop;

    // Read all geometry before updating the header or the active links.
    if (layoutChanged) {
      layoutChanged = false;
      measuredHeight = Math.ceil(nav.getBoundingClientRect().height);
      headerGap = Number.parseFloat(getComputedStyle(root).getPropertyValue('--header-gap'));
      offsets = sections.map(section => section.getBoundingClientRect().top + scrollTop);
      if (progress) {
        scrollRange = Math.max(1, root.scrollHeight - window.innerHeight);
      }
      targetTop = initialTarget?.getBoundingClientRect().top;
      initialTarget = null;
    }

    // The browser may land on a fragment before the sticky header has been measured.
    if (targetTop >= 0 && targetTop < measuredHeight) {
      scrollTop = Math.max(0, scrollTop + targetTop - measuredHeight - headerGap);
      window.scrollTo({ top: scrollTop, behavior: 'instant' });
    }

    if (measuredHeight !== headerHeight) {
      headerHeight = measuredHeight;
      root.style.setProperty('--header-height', `${headerHeight}px`);
    }

    const readingLine = scrollTop + headerHeight + headerGap + 4;
    let index = 0;
    while (offsets[index + 1] <= readingLine) index++;
    const section = sections[index];

    if (progress) {
      const fraction = Math.min(1, Math.max(0, scrollTop / scrollRange));
      progress.style.transform = `scaleX(${fraction})`;
    }
    if (section === current) return;

    const oldGroup = current?.dataset.navGroup;
    const newGroup = section.dataset.navGroup;
    if (newGroup !== oldGroup) {
      for (const link of linksByGroup.get(oldGroup) ?? []) link.removeAttribute('aria-current');
      for (const link of linksByGroup.get(newGroup)) link.setAttribute('aria-current', 'location');
    }
    current = section;
    nav.dataset.currentSection = section.id;
    title.textContent = section.dataset.readingTitle;
  }

  function scheduleUpdate() {
    if (!frame) frame = requestAnimationFrame(update);
  }

  function invalidateLayout() {
    layoutChanged = true;
    scheduleUpdate();
  }

  function focusSection() {
    const section = document.getElementById(location.hash.slice(1));
    if (section?.matches('.sheet') && document.activeElement !== section) {
      section.focus({ preventScroll: true });
    }
    scheduleUpdate();
  }

  document.addEventListener('click', event => {
    if (!menu.contains(event.target)) menu.open = false;
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[href^="#"]');
    const contents = link?.closest('.header-index, .atlas-mobile-index');
    if (contents) contents.open = false;
    link?.closest('.source-popover')?.hidePopover?.();
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Tab' && !event.defaultPrevented) {
      const popover = event.target.closest('.source-popover');
      if (popover) {
        // Let the browser move focus before dismissing the non-modal popover.
        requestAnimationFrame(() => {
          if (!popover.contains(document.activeElement)) popover.hidePopover();
        });
      }
    }
    if (event.key !== 'Escape' || !menu.open) return;
    menu.open = false;
    menu.querySelector('summary').focus();
  });

  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', invalidateLayout);
  window.addEventListener('hashchange', focusSection);
  window.addEventListener('pageshow', event => {
    if (!event.persisted && performance.getEntriesByType('navigation')[0]?.type === 'navigate') {
      initialTarget = document.getElementById(location.hash.slice(1));
    }
    invalidateLayout();
  });

  const sizes = new ResizeObserver(invalidateLayout);
  sizes.observe(nav, { box: 'border-box' });
  sizes.observe(main, { box: 'border-box' });

  initSectionMotion(sections.slice(1));
}

function initSectionMotion(sections) {
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const unseen = new Set(sections);
  const observer = new IntersectionObserver(entries => {
    if (motion.matches) return;
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const section = entry.target;
      unseen.delete(section);
      observer.unobserve(section);
      if (entry.boundingClientRect.top <= 80) continue;
      section.classList.add('just-entered');
      section.addEventListener('animationend', () => {
        section.classList.remove('just-entered');
      }, { once: true });
    }
  }, { threshold: 0.04 });

  function updateMotion() {
    observer.disconnect();
    if (motion.matches) {
      for (const section of sections) section.classList.remove('just-entered');
    } else {
      for (const section of unseen) observer.observe(section);
    }
  }

  motion.addEventListener('change', updateMotion);
  updateMotion();
}

initNavigation();
