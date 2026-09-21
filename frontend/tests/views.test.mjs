import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../src/views.js', import.meta.url), 'utf8');
const { profileCard } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
globalThis.document = {
  createElement(tag) {
    return { tag, children: [], textContent: '', setAttribute() {},
      append(...children) { this.children.push(...children); } };
  },
};
const profile = {
  job_related_attributes: { education: '本科', experience_years: 3, skills: ['Python'] },
  protected_attributes: { gender: '女性', age: 26 },
};
const text = node => [node.textContent, ...node.children.flatMap(text)].flat();
assert.ok(!text(profileCard(profile)).includes('婚姻状况'));
for (const status of ['未婚', '已婚', '离异', '丧偶']) {
  profile.protected_attributes.marital_status = status;
  const rendered = text(profileCard(profile));
  assert.equal(rendered[rendered.indexOf('婚姻状况') + 1], status);
}
console.log('Profile checks passed: all marital statuses and older profiles without marital status.');
