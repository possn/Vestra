/* Vestra weekly events navigation companion v1.1 */
(() => {
  'use strict';

  const MAX_WEEK_OFFSET = 52;
  let weekOffset = 0;

  function shiftedDate(base = new Date(), offset = weekOffset) {
    const date = new Date(base);
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() + (Number(offset) || 0) * 7);
    return date;
  }

  function labelForOffset() {
    if (weekOffset === 0) return 'Esta semana';
    if (weekOffset === -1) return 'Semana anterior';
    if (weekOffset === 1) return 'Semana seguinte';
    return weekOffset < 0 ? `${Math.abs(weekOffset)} semanas atrás` : `Daqui a ${weekOffset} semanas`;
  }

  function makeButton(action, label, text, disabled) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.weeklyWeekAction = action;
    button.textContent = text;
    button.setAttribute('aria-label', label);
    button.disabled = disabled;
    return button;
  }

  function decorate() {
    const card = document.getElementById('dashboardWeeklyEventsCard');
    const head = card?.querySelector?.('.weekly-events-head');
    if (!card || !head || head.querySelector('[data-weekly-week-nav]')) return false;

    const nav = document.createElement('div');
    nav.dataset.weeklyWeekNav = '1';
    const previous = makeButton('prev', 'Semana anterior', '‹', weekOffset <= -MAX_WEEK_OFFSET);
    const current = makeButton('today', 'Voltar à semana atual', labelForOffset(), weekOffset === 0);
    const next = makeButton('next', 'Semana seguinte', '›', weekOffset >= MAX_WEEK_OFFSET);
    nav.append(previous, current, next);
    head.appendChild(nav);
    return true;
  }

  function renderOffset(base = new Date()) {
    const api = window.VestraWeeklyEvents;
    if (!api?.render) return [];
    const events = api.render({ now: shiftedDate(base) });
    decorate();
    return events;
  }

  function move(delta, base = new Date()) {
    weekOffset = Math.max(-MAX_WEEK_OFFSET, Math.min(MAX_WEEK_OFFSET, weekOffset + delta));
    return renderOffset(base);
  }

  function reset(base = new Date()) {
    weekOffset = 0;
    return renderOffset(base);
  }

  document.addEventListener('click', event => {
    const action = event.target.closest?.('[data-weekly-week-action]')?.dataset?.weeklyWeekAction;
    if (action === 'prev') { move(-1); return; }
    if (action === 'next') { move(1); return; }
    if (action === 'today') { reset(); return; }
    if (event.target.closest?.('.sidenavbtn[data-view="dashboard"], .navbtn[data-view="dashboard"]')) {
      weekOffset = 0;
      setTimeout(decorate, 0);
    }
  });

  const observer = typeof MutationObserver === 'function'
    ? new MutationObserver(() => { if (decorate()) observer.disconnect(); })
    : null;
  if (observer && document.documentElement) observer.observe(document.documentElement, { childList: true, subtree: true });
  window.addEventListener?.('vestra:market-ready', () => setTimeout(decorate, 0));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(decorate, 0), { once: true });
  else setTimeout(decorate, 0);

  window.VestraWeeklyEventsNavigation = Object.freeze({
    shiftedDate,
    renderOffset,
    move,
    reset,
    getWeekOffset: () => weekOffset,
    maxWeekOffset: MAX_WEEK_OFFSET,
    version: '1.1',
  });
})();
