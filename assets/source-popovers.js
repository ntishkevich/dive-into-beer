const sourcePopoverSelector = 'dialog[popover][id^="source-popover:"]';
const sourceTriggers = [...document.querySelectorAll('.source-trigger')];
const sourceHeader = document.querySelector('.topnav');
let sourceInvoker;
let sourceHistoryState = history.state;

function showSourceEntry(entry) {
  entry.querySelector('.source-trigger').focus({ preventScroll: true });
  entry.scrollIntoView({ behavior: 'instant' });
}

document.addEventListener('click', event => {
  if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  const trigger = event.target.closest('.source-trigger');
  if (trigger) sourceInvoker = trigger;

  const jump = event.target.closest('.source-popover__jump');
  const popover = jump?.closest(sourcePopoverSelector);
  if (!popover) return;
  const { hash } = jump;
  const entry = document.getElementById(hash.slice(1));
  if (!entry) return;

  if (hash !== location.hash) {
    const sourceReturn = { destination: hash, scrollY: window.scrollY };
    const origin = sourceInvoker?.getAttribute('popovertarget') === popover.id ? sourceInvoker : null;
    const originRect = origin?.getBoundingClientRect();
    if (originRect && originRect.top >= sourceHeader.getBoundingClientRect().bottom &&
      originRect.bottom <= window.innerHeight) {
      sourceReturn.invoker = sourceTriggers.indexOf(origin);
      sourceReturn.offset = originRect.top;
    }

    history.replaceState({
      ...history.state,
      sourceReturn,
    }, '');
    history.pushState({ sourceDestination: hash }, '', hash);
    sourceHistoryState = history.state;
  }

  event.preventDefault();
  popover.hidePopover();
  showSourceEntry(entry);
});

// The section navigation handles hashchange first. Restore the citation and its focus afterward.
window.addEventListener('hashchange', () => {
  const previous = sourceHistoryState;
  sourceHistoryState = history.state;
  const sourceReturn = sourceHistoryState?.sourceReturn;
  const destination = sourceHistoryState?.sourceDestination;

  if (sourceReturn && sourceReturn.destination === previous?.sourceDestination) {
    const invoker = sourceTriggers[sourceReturn.invoker];
    let top = sourceReturn.scrollY;
    if (invoker) {
      const rect = invoker.getBoundingClientRect();
      const headerBottom = sourceHeader.getBoundingClientRect().bottom;
      const offset = Math.max(headerBottom, Math.min(sourceReturn.offset, window.innerHeight - rect.height));
      top = window.scrollY + rect.top - offset;
      invoker.focus({ preventScroll: true });
    }
    window.scrollTo({ top, behavior: 'instant' });
  } else if (destination && destination === previous?.sourceReturn?.destination) {
    const entry = document.getElementById(destination.slice(1));
    if (entry) showSourceEntry(entry);
  }
});

for (const jump of document.querySelectorAll('.source-popover__jump')) {
  jump.removeAttribute('target');
  jump.removeAttribute('aria-describedby');
}

document.addEventListener('keydown', event => {
  if (event.key !== 'Tab' || event.defaultPrevented) return;
  const popover = event.target.closest(sourcePopoverSelector);
  if (!popover) return;

  // Let the browser move focus before closing the non-modal popover.
  requestAnimationFrame(() => {
    if (!popover.contains(document.activeElement)) popover.hidePopover();
  });
});
