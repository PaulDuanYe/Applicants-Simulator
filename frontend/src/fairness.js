import { element, button } from './views.js';

const options = [
  ['age_discrimination', '我认为存在年龄歧视'], ['gender_discrimination', '我认为存在性别歧视'],
  ['experience_overemphasis', '我认为结果过于看重工作经验'], ['education_overemphasis', '我认为结果过于看重学历'],
  ['skills_overemphasis', '我认为结果过于看重技能'], ['other', '其他看法'],
  ['none', '我认为没有上述问题'], ['unsure', '我不确定'],
];

export function renderFairness(root, state, submit, changed) {
  const key = `research_fairness_${state.case_id}`;
  let draft;
  try { draft = JSON.parse(sessionStorage.getItem(key)); } catch { /* Discard malformed local draft. */ }
  if (!draft || typeof draft !== 'object' || Array.isArray(draft)) draft = {};
  draft.group_selections = Array.isArray(draft.group_selections) ? draft.group_selections : [];
  draft.comparisons = Array.isArray(draft.comparisons) ? draft.comparisons.filter(p => p && typeof p === 'object').slice(0, 9) : [];
  const form = element('form', '', { class: 'fairness-form' });
  form.append(element('h2', '分享你的看法'), element('p', '三个问题都需要回答，请按自己的想法填写。理由最多 5000 字。', { class: 'muted' }));
  const save = () => sessionStorage.setItem(key, JSON.stringify(draft));
  function section(title) {
    const field = element('fieldset', ''); field.append(element('legend', title)); form.append(field); return field;
  }
  function textarea(parent, label, object, field) {
    const wrap = element('label', label);
    const input = element('textarea', '', { rows: '3', maxlength: '5000', required: '' });
    input.value = typeof object[field] === 'string' ? object[field] : '';
    input.addEventListener('input', () => { object[field] = input.value; input.setCustomValidity(''); save(); });
    wrap.append(input); parent.append(wrap);
  }
  const rating = section('1. 你觉得结果公平吗？');
  rating.append(element('p', '总体来说，你觉得这六人的筛选结果有多公平？'), element('p', '1 = 非常不公平；10 = 非常公平'));
  const scale = element('div', '', { class: 'rating-scale' });
  for (let n = 1; n <= 10; n++) {
    const label = element('label', ''); const input = element('input', '', { type: 'radio', name: 'fairness_rating', value: String(n), required: '' });
    input.checked = draft.fairness_rating === n;
    input.addEventListener('change', () => { draft.fairness_rating = n; save(); });
    label.append(input, element('span', String(n))); scale.append(label);
  }
  rating.append(scale);
  const group = section('2. 你怎么看整体结果？');
  group.append(element('p', '你认为这些结果有哪些情况？（可多选，至少选一项）'),
    element('p', '请选择符合你看法的选项。选择“没有上述问题”或“不确定”时，不能同时选其他项。'));
  const checks = [];
  const otherBox = element('div', '');
  function syncGroup() {
    for (const input of checks) input.checked = draft.group_selections.includes(input.value);
    otherBox.hidden = !draft.group_selections.includes('other');
    otherBox.querySelector('textarea').required = !otherBox.hidden;
  }
  for (const [value, text] of options) {
    const label = element('label', '', { class: 'survey-choice' }); const input = element('input', '', { type: 'checkbox', value });
    input.addEventListener('change', () => {
      if (input.checked) draft.group_selections = ['none', 'unsure'].includes(value) ? [value] : [...draft.group_selections.filter(x => !['none', 'unsure', value].includes(x)), value];
      else draft.group_selections = draft.group_selections.filter(x => x !== value);
      checks[0].setCustomValidity(''); syncGroup(); save();
    });
    checks.push(input); label.append(input, element('span', text)); group.append(label);
  }
  textarea(otherBox, '其他看法是什么？（必填）', draft, 'other_group_view'); group.append(otherBox); syncGroup();
  textarea(group, '为什么这样选？请结合简历或筛选结果说明理由。（必填）', draft, 'group_reason');
  const individual = section('3. 你想比较哪些申请者？');
  individual.append(element('p', '你觉得有没有人虽然没通过，却比某位已通过的人更适合这个岗位？'));
  const details = element('div', '');
  function drawDetails() {
    details.replaceChildren();
    if (draft.individual_comparison === 'yes') {
      details.append(element('p', '每组选择两个人，并分别说明理由。你可以添加多组比较，同一个人可以出现在不同组中。', { class: 'muted' }));
      draft.comparisons.forEach((pair, index) => {
        const card = element('section', '', { class: 'comparison-card' }); card.append(element('h3', `比较 ${index + 1}`));
        for (const [field, decision, labelText] of [['rejected_profile_id', 'reject', '未通过、但你认为更适合的人'], ['passed_profile_id', 'pass', '你想与哪位已通过的人比较？']]) {
          const label = element('label', labelText); const select = element('select', '', { required: '' });
          select.append(element('option', '请选择申请者', { value: '' }));
          for (const a of state.applicants.filter(a => a.revealed_decision === decision)) select.append(element('option', a.applicant_role === 'participant' ? '你' : `竞争者 ${a.display_position - 1}`, { value: a.profile_id }));
          select.value = pair[field] || '';
          select.addEventListener('change', () => { pair[field] = select.value; for (const s of details.querySelectorAll('select')) s.setCustomValidity(''); save(); });
          label.append(select); card.append(label);
        }
        card.append(element('p', '你认为前者比后者更适合这个岗位。')); textarea(card, '为什么你觉得前者更适合？请结合两人的简历和岗位要求说明。（必填）', pair, 'reason');
        card.append(button('删除这组比较', () => { draft.comparisons.splice(index, 1); save(); drawDetails(); }, true)); details.append(card);
      });
      if (draft.comparisons.length < 9) details.append(button('添加一组比较', () => { draft.comparisons.push({}); save(); drawDetails(); }, true));
    } else if (['no', 'unsure'].includes(draft.individual_comparison)) textarea(details, '为什么这样选？你也可以谈谈某个人的筛选结果。（必填）', draft, 'individual_reason');
    changed();
  }
  for (const [value, text] of [['yes', '有'], ['no', '没有'], ['unsure', '不确定']]) {
    const label = element('label', '', { class: 'survey-choice' }); const input = element('input', '', { type: 'radio', name: 'individual_comparison', value, required: '' });
    input.checked = draft.individual_comparison === value;
    input.addEventListener('change', () => { draft.individual_comparison = value; if (value === 'yes' && !draft.comparisons.length) draft.comparisons.push({}); save(); drawDetails(); });
    label.append(input, element('span', text)); individual.append(label);
  }
  individual.append(details);
  const error = element('p', '', { role: 'alert' }); form.append(error);
  const finish = element('button', '提交反馈，结束本次参与', { type: 'submit' }); form.append(finish);
  form.addEventListener('submit', event => {
    event.preventDefault(); error.textContent = '';
    if (!draft.group_selections.length) { checks[0].setCustomValidity('请至少选择一项。'); checks[0].reportValidity(); return; }
    for (const input of form.querySelectorAll('textarea[required]')) if (!input.value.trim()) { input.setCustomValidity('请写下你的理由。'); input.reportValidity(); return; }
    const pairs = draft.individual_comparison === 'yes' ? draft.comparisons : [];
    if (draft.individual_comparison === 'yes' && !pairs.length) { error.textContent = '请至少添加一组比较。'; return; }
    if (new Set(pairs.map(p => `${p.rejected_profile_id}/${p.passed_profile_id}`)).size !== pairs.length) { error.textContent = '这两个人已经比较过了，请删除重复的一组。'; return; }
    submit('submit_fairness', { fairness_rating: draft.fairness_rating, group_selections: draft.group_selections,
      group_reason: draft.group_reason, other_group_view: draft.group_selections.includes('other') ? draft.other_group_view : null,
      individual_comparison: draft.individual_comparison, individual_reason: draft.individual_comparison === 'yes' ? null : draft.individual_reason,
      comparisons: pairs });
  });
  root.append(form); drawDetails();
}
