import { element, button, profileCard } from './views.js';

export function judgmentsReady(root) {
  const chosen = [...root.querySelectorAll('.competition-grid input:checked')];
  return chosen.length === 6 && chosen.filter(input => input.value === 'pass').length === 3;
}

export function renderCompetition(root, state, submit, changed) {
  const draftKey = `research_judgments_${state.case_id}`;
  let draft = {};
  try { draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}'); } catch { /* Invalid local draft: start unselected. */ }
  if (!draft || typeof draft !== 'object' || Array.isArray(draft)) draft = {};
  root.append(element('p', '第 3 步 · 判断谁应该通过', { class: 'eyebrow' }), element('h1', '你认为谁应该通过筛选？'),
    element('p', '下面是你和另外五位申请者的简历。请结合岗位要求作出判断。'),
    element('p', '请为每人选择“通过”或“不通过”：三人通过，三人不通过。'),
    element('p', '选好六人后，点击“确认并查看结果”。提交后不能修改。'));
  const job = element('section', null);
  job.append(element('h2', state.selected_job.title), element('p', state.selected_job.description));
  root.append(job);
  const grid = element('div', null, { class: 'competition-grid' });
  const counter = element('p', '', { role: 'status', 'aria-live': 'polite' });
  const confirm = button('确认并查看结果', () => submit('submit_and_reveal', {
    judgments: state.applicants.map(a => ({ profile_id: a.profile_id, judgment: draft[a.profile_id] })),
  }));
  confirm.dataset.requiresJudgments = 'true';
  function update() {
    const values = state.applicants.map(a => draft[a.profile_id]);
    const passes = values.filter(v => v === 'pass').length;
    const rejects = values.filter(v => v === 'reject').length;
    counter.textContent = `已选择 ${passes + rejects}/6 · 通过 ${passes}/3 · 不通过 ${rejects}/3`;
    changed();
  }
  for (const applicant of state.applicants) {
    const label = applicant.applicant_role === 'participant' ? '你' : `竞争者 ${applicant.display_position - 1}`;
    const card = profileCard(applicant.profile);
    card.querySelector('h2').textContent = label;
    const choices = element('fieldset', null);
    choices.append(element('legend', label === '你' ? '你认为自己应该通过吗？' : `你认为${label}应该通过吗？`));
    for (const [value, text] of [['pass', '通过'], ['reject', '不通过']]) {
      const option = element('label', null, { class: 'judgment-option' });
      const input = element('input', null, { type: 'radio', name: `judgment-${applicant.profile_id}`, value });
      input.checked = draft[applicant.profile_id] === value;
      input.addEventListener('change', () => {
        draft[applicant.profile_id] = value;
        sessionStorage.setItem(draftKey, JSON.stringify(draft)); update();
      });
      option.append(input, element('span', text)); choices.append(option);
    }
    card.append(choices); grid.append(card);
  }
  root.append(grid, counter, confirm); update();
}
