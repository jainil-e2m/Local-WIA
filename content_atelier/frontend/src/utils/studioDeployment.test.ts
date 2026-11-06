import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resetStudioForDeployment } from './studioDeployment';
import { mergeEditorialMocks } from '../data/editorialMockData';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';
import { INITIAL_IDEAS } from '../data/mockData';
import { advanceEditorialItem } from './editorialWorkflow';
import { approvePackForScheduling, schedulePack } from './publishingSchedule';

test('redeployments reset only the four sourced workflows, while same-deployment reloads retain approvals', () => {
  const ids = new Set(FATHOM_WEEKLY_ANGLES.map(idea => idea.id));
  const library = resetStudioForDeployment(mergeEditorialMocks(INITIAL_IDEAS), 'deployment-one');
  const source = library.find(idea => ids.has(idea.id))!;
  const generated = advanceEditorialItem(advanceEditorialItem(source, 'gate2_brief', '2026-10-06T12:00:00Z'), 'gate3_pack', '2026-10-06T12:05:00Z');
  const scheduled = schedulePack(approvePackForScheduling(generated, '2026-10-06T12:10:00Z'), '2026-10-10', '10:00', Date.parse('2026-10-06T12:10:00Z'));
  scheduled.brief = { ...scheduled.brief, coreInsight: 'Saved editorial revision' };
  scheduled.pack!.email.body = 'Saved email revision';
  const saved = library.map(idea => idea.id === source.id ? scheduled : idea);
  assert.deepEqual(resetStudioForDeployment(JSON.parse(JSON.stringify(saved)), 'deployment-one'), JSON.parse(JSON.stringify(saved)));
  const redeployed = resetStudioForDeployment(saved, 'deployment-two');
  for (const item of redeployed.filter(idea => ids.has(idea.id))) {
    const previous = saved.find(idea => idea.id === item.id)!;
    assert.equal(item.mockDeploymentId, 'deployment-two');
    assert.equal(item.gate, 'gate1_angle');
    for (const field of ['angleApprovedAt', 'briefApprovedAt', 'publishingApprovedAt', 'scheduledAt', 'pack', 'mockSimulation'] as const) assert.equal(item[field], undefined);
    assert.equal(item.brief, previous.brief);
    assert.equal(item.editorialContext, previous.editorialContext);
  }
  assert.equal(redeployed.find(idea => idea.id === source.id)!.mockContentPack!.email.body, 'Saved email revision');
  for (const item of saved.filter(idea => !ids.has(idea.id))) assert.equal(redeployed.find(idea => idea.id === item.id), item);
  assert.deepEqual(resetStudioForDeployment(redeployed, 'deployment-two'), redeployed);
});
