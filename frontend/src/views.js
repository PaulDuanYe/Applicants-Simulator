// Render dataset strings with textContent, never HTML interpolation.
export function element(tag, text, attrs = {}) {
  const node = document.createElement(tag);
  if (text !== null) node.textContent = text;
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}
export function button(label, action, secondary = false) {
  const node = element('button', label, { type: 'button', ...(secondary ? { class: 'secondary' } : {}) });
  node.addEventListener('click', action);
  return node;
}
export function profileCard(profile) {
  const card = element('section', null, { class: 'profile' });
  card.append(element('h2', '你的简历'));
  const attributes = profile.job_related_attributes;
  const demographic = profile.protected_attributes;
  const list = element('dl', null);
  for (const [label, value] of [['教育背景', attributes.education], ['工作经验', `${attributes.experience_years} 年`],
    ['技能', attributes.skills.join('、')], ['性别', demographic.gender], ['年龄', `${demographic.age} 岁`]]) {
    list.append(element('dt', label), element('dd', value));
  }
  if (demographic.marital_status) {
    list.append(element('dt', '婚姻状况'), element('dd', demographic.marital_status));
  }
  card.append(list);
  return card;
}
export function renderProfile(root, state, act) {
  root.append(element('p', '第 1 步 · 阅读简历', { class: 'eyebrow' }), element('h1', '你在模拟中的简历'),
    element('p', '你将使用以下简历参与招聘模拟。请先阅读简历内容。'), profileCard(state.profile));
  root.append(element('p', '继续后，简历不能再更换。', { class: 'muted' }));
  if (state.profile_refresh_enabled !== false) root.append(button('换一份简历', () => act('refresh'), true));
  root.append(button('继续，查看岗位', () => act('confirm_profile')));
}
export function renderJobs(root, state, act) {
  if (state.job_selection_enabled === false) {
    const job = state.jobs[0];
    root.append(element('p', '第 2 步 · 阅读岗位', { class: 'eyebrow' }), element('h1', '你将申请的岗位'),
      element('p', '请阅读岗位介绍。接下来，你将查看其他申请者，并判断哪些人应该通过筛选。'), profileCard(state.profile));
    const description = element('section', null, { class: 'profile' });
    description.append(element('h2', job.title), element('p', job.description));
    root.append(description, button('继续，查看申请者', () => act('confirm_job', { job_id: job.job_id })));
    return;
  }
  root.append(element('p', '第 2 步 · 选择岗位', { class: 'eyebrow' }), element('h1', '选择你要申请的岗位'), profileCard(state.profile));
  const options = element('fieldset', null);
  options.append(element('legend', '选择一个想申请的岗位。确认后，你将查看其他申请者并作出判断。'));
  const confirm = button('确认岗位，继续', () => {
    const selected = options.querySelector('input:checked');
    if (selected) act('confirm_job', { job_id: selected.value });
  });
  confirm.dataset.requiresSelection = 'true';
  confirm.disabled = true;
  for (const job of state.jobs) {
    const label = element('label', null, { class: 'job-option' });
    const radio = element('input', null, { type: 'radio', name: 'job', value: job.job_id });
    radio.addEventListener('change', () => { confirm.disabled = false; });
    const description = element('span', null);
    description.append(element('strong', job.title), element('span', job.description, { class: 'description' }));
    label.append(radio, description); options.append(label);
  }
  root.append(options, element('p', '确认后不能更改岗位。', { class: 'muted' }), confirm);
}
