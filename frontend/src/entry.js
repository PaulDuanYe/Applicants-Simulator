import { element, button } from './views.js';

export function intro(root, next) {
  root.className = 'entry-page intro-page';
  const copy = element('div', null, { class: 'intro-copy' });
  copy.append(element('h1', '招聘情境模拟器'),
    element('p', '在这里，你将以求职者的身份体验招聘情境。'),
    element('p', '点击“开始”，进入模拟。', { class: 'muted' }));
  const footer = element('div', null, { class: 'entry-footer' });
  footer.append(button('开始', next));
  root.append(copy, footer);
}

export function codeEntry(root, model, callbacks) {
  root.className = 'entry-page code-page';
  const heading = element('header', null, { class: 'entry-heading' });
  heading.append(element('h1', '准备开始'), element('p', '请保存你的参与代码，下次可以用它找回记录。'),
    element('p', '第一次来，请先生成代码；已有代码，直接输入即可。'));
  const cards = element('div', null, { class: 'code-grid' });
  const fresh = element('section', null, { class: 'code-card', 'aria-labelledby': 'new-heading' });
  fresh.append(element('h2', '首次参与', { id: 'new-heading' }));
  if (model.generated) {
    fresh.setAttribute('tabindex', '0');
    fresh.setAttribute('aria-label', '使用生成的参与代码');
    fresh.append(element('p', '你的参与代码'), element('p', model.generated.participant_code, { class: 'participant-code' }),
      element('p', '请记下或复制这串代码，下次参与时还会用到。'), element('p', '保存好代码后，点击“开始模拟”。', { class: 'muted' }));
  } else {
    fresh.append(element('p', '还没有参与代码？点击下方按钮生成一个。'), button('生成参与代码', callbacks.generate, true));
  }
  const returning = element('section', null, { class: 'code-card', 'aria-labelledby': 'return-heading' });
  returning.append(element('h2', '再次参与', { id: 'return-heading' }), element('p', '输入保存的代码，找回之前的记录。'));
  const input = element('input', null, { id: 'participant-code', autocomplete: 'off', maxlength: '40',
    placeholder: '请输入你的参与代码', 'aria-describedby': 'code-error' });
  input.value = model.code;
  const error = element('p', '', { id: 'code-error', class: 'field-error', role: 'alert' });
  error.hidden = true;
  returning.append(element('label', '参与代码', { for: 'participant-code' }), input, error);
  const footer = element('div', null, { class: 'entry-footer' });
  const begin = button('开始模拟', callbacks.begin);
  begin.dataset.requiresIdentity = 'true';
  footer.append(begin);
  function select(path) {
    if (root.getAttribute('aria-busy') === 'true') return;
    model.path = path;
    if (path === 'generated') { error.hidden = true; input.removeAttribute('aria-invalid'); }
    fresh.classList.toggle('active', path === 'generated');
    returning.classList.toggle('active', path === 'existing');
    callbacks.changed();
  }
  input.addEventListener('input', () => {
    model.code = input.value; error.hidden = true; input.removeAttribute('aria-invalid'); select('existing');
  });
  input.addEventListener('focus', () => select('existing'));
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !begin.disabled) { event.preventDefault(); callbacks.begin(); }
  });
  fresh.addEventListener('click', () => { if (model.generated) select('generated'); });
  fresh.addEventListener('keydown', event => {
    if (model.generated && ['Enter', ' '].includes(event.key)) { event.preventDefault(); select('generated'); }
  });
  cards.append(fresh, returning); root.append(heading, cards, footer);
  fresh.classList.toggle('active', model.path === 'generated');
  returning.classList.toggle('active', model.path === 'existing');
  select(model.path);
}
