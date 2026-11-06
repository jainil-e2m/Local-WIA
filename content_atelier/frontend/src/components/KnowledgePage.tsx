import React from 'react';
import { ContextReview } from './ContextReview';
import { ContextKnowledge } from './ContextKnowledge';
import { ContextVersions } from './ContextVersions';
import { PageTabs } from './AdminParts';
import { paths } from '../app/routes';

/* Knowledge, for the team (behind the context flag): the review queue, what the system knows and the knowledge-base
   versions. Each tab is a path (`/knowledge/review`, `/knowledge/known`, `/knowledge/versions`) and draws the page header
   with its own subtitle and buttons; an entry's history and a version's changes have paths of their own below those. */

export const KNOWLEDGE_TABS = [['review', 'Review queue'], ['known', 'What the system knows'], ['versions', 'Versions']] as const;
export type KnowledgeTab = typeof KNOWLEDGE_TABS[number][0];
const TAB_PATHS: Record<KnowledgeTab, string> = { review: paths.review, known: paths.known, versions: paths.versions };

export function KnowledgePage({ tab = 'review' }: { tab?: KnowledgeTab }) {
  return <div className="space-y-6 pb-12 text-[#1B2433]">
    <PageTabs label="Knowledge" tabs={KNOWLEDGE_TABS.map(([id, label]) => [id, label, TAB_PATHS[id]] as const)} current={tab} />
    {tab === 'review' && <ContextReview />}
    {tab === 'known' && <ContextKnowledge />}
    {tab === 'versions' && <ContextVersions />}
  </div>;
}
