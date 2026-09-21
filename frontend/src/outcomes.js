import { element, profileCard } from './views.js';
import { renderFairness } from './fairness.js';

export function renderOutcomes(root, state, submit, changed) {
  root.append(element('h1', '查看结果，分享你的看法'),
    element('p', '先看看筛选结果，再填写下方三个问题。填写时可以回看简历。'));
  const job = element('section', '', { class: 'card' });
  job.append(element('h2', state.selected_job.title), element('p', state.selected_job.description));
  const grid = element('div', '', { class: 'competition-grid' });
  const label = decision => decision === 'pass' ? '通过' : '不通过';
  for (const applicant of state.applicants) {
    const card = profileCard(applicant.profile);
    card.querySelector('h2').textContent = applicant.applicant_role === 'participant' ? '你' : `竞争者 ${applicant.display_position - 1}`;
    card.append(element('p', `你的判断：${label(applicant.participant_judgment)}`),
      element('p', `筛选结果：${label(applicant.revealed_decision)}`));
    if (applicant.participant_judgment !== applicant.revealed_decision) card.append(element('p', '与你的判断不同', { class: 'prediction-difference' }));
    grid.append(card);
  }
  root.append(job, grid);
  renderFairness(root, state, submit, changed);
}
