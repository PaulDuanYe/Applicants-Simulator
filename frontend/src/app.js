import { renderOutcomes } from './outcomes.js';
import { request } from './api.js';
import { renderCompetition, judgmentsReady } from './competition.js';
import { intro, codeEntry } from './entry.js';
import { VisibleTimer } from './timing.js';
import { element, button, renderProfile, renderJobs } from './views.js';

const root = document.querySelector('#screen');
const status = document.querySelector('#status');
const recovery = document.querySelector('#recovery');
const tabId = crypto.randomUUID();
const timer = new VisibleTimer();
let token = localStorage.getItem('research_token') || '';
let state = null;
let busy = false;
let blocked = false;
let pending = null;
let entryModel = { generated: JSON.parse(sessionStorage.getItem('research_generated') || 'null'), code: '', path: 'generated' };
function identityReady() {
  return entryModel.path === 'generated' ? Boolean(entryModel.generated) : Boolean(entryModel.code.trim());
}

function setBusy(value) {
  const focusedControl = document.activeElement;
  busy = value;
  root.setAttribute('aria-busy', String(value || blocked));
  for (const control of root.querySelectorAll('button,input,select,textarea')) {
    control.disabled = value || blocked || (state?.phase === 'outcomes' && !state.survey_ack) || (state && !state.ack && ['profile', 'job', 'competition', 'outcomes'].includes(state.phase)) ||
      (control.dataset.requiresJudgments === 'true' && !judgmentsReady(root)) ||
      (control.dataset.requiresIdentity === 'true' && !identityReady()) ||
      (control.dataset.requiresSelection === 'true' && !root.querySelector('input[name="job"]:checked'));
    if (control.tagName === 'BUTTON') {
      if (value && focusedControl === control && pending && !['timing', 'display'].includes(pending.body.op)) {
        control.dataset.idleLabel ||= control.textContent;
        control.textContent = '处理中…';
      } else if (!value && control.dataset.idleLabel) {
        control.textContent = control.dataset.idleLabel;
        delete control.dataset.idleLabel;
      }
    }
  }
}
function message(text, error = false) {
  status.hidden = !error;
  status.textContent = text;
  status.dataset.state = error ? 'error' : 'ready';
}
function clearScreen() { root.replaceChildren(); root.className = ''; recovery.replaceChildren(); message(''); }
function resumeTimer() {
  if (!busy && !blocked && state?.ack && ['profile', 'job', 'competition', 'outcomes'].includes(state.phase)) timer.resume();
}
function failure(error) {
  const codeError = pending?.body.op === 'login' && error.status === 404 && document.querySelector('#code-error');
  if (codeError) {
    codeError.textContent = '没有找到这个参与代码，请检查是否输入完整。'; codeError.hidden = false;
    document.querySelector('#participant-code').setAttribute('aria-invalid', 'true');
    message('');
  } else message(error.message, true);
  recovery.replaceChildren();
  if (error.status === 0 || error.status >= 500) {
    blocked = true;
    timer.pause();
    recovery.append(button('重试', () => executePending()));
  } else {
    sessionStorage.removeItem('research_pending'); pending = null;
    if ([401, 409].includes(error.status)) {
      blocked = true; timer.pause();
      recovery.append(button('刷新页面', () => location.reload()));
      if (error.status === 401) localStorage.removeItem('research_token');
    } else { blocked = false; resumeTimer(); }
  }
}
async function executePending() {
  if (!pending || busy) return;
  const current = pending;
  let startVisit = false;
  let revealNext = false;
  setBusy(true);
  try {
    const result = await request('/api/action', current.token, current.body);
    sessionStorage.removeItem('research_pending'); pending = null; blocked = false;
    recovery.replaceChildren(); message('已连接');
    if (result.token) { token = result.token; localStorage.setItem('research_token', token); }
    if (result.feedback_saved) showFinished(current.body.case_id);
    else if (['timing', 'display'].includes(current.body.op)) state = result;
    else if (current.body.op === 'register') {
      entryModel.generated = result; entryModel.path = 'generated';
      sessionStorage.setItem('research_generated', JSON.stringify(result)); showEntry();
    } else if (current.body.op === 'login' && !result.active) startVisit = true;
    else if (result.phase === 'judged') {
      // Replay of a pre-upgrade submission receipt: continue without a second click.
      state = result; timer.reset(0); revealNext = true;
    }
    else if (result.case_id) showCase(result);
    else showHub(result);
  } catch (error) { failure(error); }
  finally {
    setBusy(false);
    if (revealNext) { send('reveal_outcomes', {}, true); return; }
    if (startVisit) { send('new_session'); return; }
    if (!pending) {
      if (needsDisplay()) scheduleDisplay();
      else resumeTimer();
    }
  }
}
function send(op, extras = {}, caseOperation = false) {
  if (busy || pending || blocked) return;
  if (op !== 'timing') timer.pause();
  const body = { op, action_id: crypto.randomUUID(), tab_id: tabId, ...extras };
  if (caseOperation) Object.assign(body, { case_id: state.case_id, revision: state.revision,
    presentation_id: state.presentation_id, duration_ms: timer.value(), at: new Date().toISOString() });
  if (caseOperation && state.phase === 'outcomes') body.survey_version = 'stage5_v1';
  pending = { body, token };
  sessionStorage.setItem('research_pending', JSON.stringify(pending));
  executePending();
}
function showHub(person) {
  timer.pause(); state = null; clearScreen(); sessionStorage.removeItem('research_case');
  root.append(element('p', '招聘情境模拟', { class: 'eyebrow' }), element('h1', '欢迎参与'),
    element('p', '这是你的参与代码，请保存好。下次输入它，就能找回记录。'),
    element('p', person.participant_code, { class: 'participant-code' }));
  if (person.active) {
    root.append(button('继续上次参与', () => send('claim', { case_id: person.active.case_id })),
      element('p', '选择“重新开始”会结束上次参与，之前保存的记录仍会保留。'));
  }
  root.append(button('重新开始', () => send('new_session'), true), button('使用其他参与代码', () => {
    localStorage.removeItem('research_token'); token = ''; showEntry();
  }, true));
}
function showIntro() {
  state = null; timer.pause(); clearScreen();
  sessionStorage.removeItem('research_entry_page');
  intro(root, showEntry);
}
function showEntry() {
  state = null; timer.pause(); clearScreen();
  sessionStorage.setItem('research_entry_page', 'code');
  codeEntry(root, entryModel, {
    generate: () => send('register'),
    changed: () => setBusy(busy),
    begin: () => {
      if (!identityReady() || busy || blocked) return;
      if (entryModel.path === 'existing') send('login', { code: entryModel.code.trim() });
      else {
        token = entryModel.generated.token; localStorage.setItem('research_token', token);
        send('new_session');
      }
    },
  });
  setBusy(busy);
}
function showCase(next) {
  sessionStorage.removeItem('research_entry_page');
  sessionStorage.removeItem('research_generated');
  entryModel.generated = null;
  sessionStorage.setItem('research_case', next.case_id);
  state = next; timer.reset(next.duration_ms); clearScreen();
  if (next.phase === 'profile') renderProfile(root, next, (op, extras) => send(op, extras, true));
  else if (next.phase === 'job') renderJobs(root, next, (op, extras) => send(op, extras, true));
  else if (next.phase === 'competition') renderCompetition(root, next, (op, extras) => send(op, extras, true), () => setBusy(busy));
  else if (next.phase === 'outcomes') {
    sessionStorage.removeItem(`research_judgments_${next.case_id}`);
    renderOutcomes(root, next, (op, extras) => send(op, extras, true), () => setBusy(busy));
  }
  else if (next.phase === 'saved') {
    // An old persisted action receipt can still return the former terminal phase.
    root.append(element('h1', '岗位选择已保存'), button('继续作出判断', () => send('claim', { case_id: next.case_id })));
  }
  root.querySelector('h1')?.setAttribute('tabindex', '-1'); root.querySelector('h1')?.focus();
}
function showFinished(caseId) {
  timer.pause(); state = null; clearScreen();
  sessionStorage.removeItem(`research_fairness_${caseId}`); sessionStorage.removeItem('research_case');
  root.append(element('h1', '你的反馈已保存，感谢参与！'));
}
function needsDisplay() { return state && (!state.ack || (state.phase === 'outcomes' && !state.survey_ack)); }
function scheduleDisplay() {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!document.hidden && needsDisplay() && !busy && !pending && !blocked) send('display', {}, true);
  }));
}
function checkpoint() {
  if (state?.ack && ['profile', 'job', 'competition', 'outcomes'].includes(state.phase) && !busy && !blocked && !pending) send('timing', {}, true);
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { timer.pause(); checkpoint(); }
  else { if (needsDisplay()) scheduleDisplay(); else resumeTimer(); }
});
window.addEventListener('pagehide', () => { timer.pause(); checkpoint(); });
setInterval(checkpoint, 5000);
async function start() {
  showIntro();
  if (sessionStorage.getItem('research_pending') || sessionStorage.getItem('research_case')) setBusy(true);
  try {
    const saved = sessionStorage.getItem('research_pending');
    if (saved) {
      const action = JSON.parse(saved);
      const result = await request('/api/action', action.token, action.body);
      if (result.token) { token = result.token; localStorage.setItem('research_token', token); }
      if (action.body.op === 'register') {
        entryModel.generated = result;
        sessionStorage.setItem('research_generated', JSON.stringify(result));
        sessionStorage.setItem('research_entry_page', 'code');
      }
      if (result.case_id) sessionStorage.setItem('research_case', result.case_id);
      sessionStorage.removeItem('research_pending');
      if (result.feedback_saved) { showFinished(action.body.case_id); return; }
      if (action.body.op === 'login') {
        if (result.active) showHub(result); else { showEntry(); setBusy(false); send('new_session'); }
        return;
      }
    }
    const prior = sessionStorage.getItem('research_case');
    if (token && prior) {
      const person = await request('/api/me', token);
      if (person.active?.case_id === prior) { setBusy(false); send('claim', { case_id: prior }); return; }
      sessionStorage.removeItem('research_case');
    }
    if (entryModel.generated) showEntry();
  } catch (error) {
    if ([401, 409].includes(error.status)) sessionStorage.removeItem('research_pending');
    if (error.status === 401) { localStorage.removeItem('research_token'); token = ''; }
    message(error.message || '暂时无法恢复进度，请刷新页面重试。', true);
    recovery.append(button('刷新页面', () => location.reload()));
  } finally { if (!pending) setBusy(false); }
}
start();
