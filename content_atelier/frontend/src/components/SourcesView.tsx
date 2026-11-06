import React from 'react';
import { useAuth } from '../auth/AuthProvider';
import { paths } from '../app/routes';
import { useMe } from '../utils/me';
import { useWeekList } from './shared/WeekPicker';
import { CyclePanel } from './CyclePanel';
import { PageHeading } from './PageHeading';
import { PageTabs } from './AdminParts';
import { LoadingState } from './shared/states';

/* Sources, for the team: every stored document, the intake that brings new ones in, the weekly cycle and the alerts and costs.
   Each tab draws its own page header (its subtitle and buttons differ). A session that is not a team session renders only
   this notice and mounts no screen that would ask for the data; the Node server also refuses the routes to it (403). */

export type SourcesTab = 'documents' | 'intake' | 'cycle' | 'alerts';
const TABS = [['documents', 'All documents', paths.documents], ['intake', 'Intake', paths.intake], ['cycle', 'Weekly cycle', paths.cycle],
  ['alerts', 'Alerts and costs', paths.alerts]] as const;

export function SourcesView({ tab, children }: { tab: SourcesTab; children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== 'team') return <><PageHeading title="Sources" /><p className="p-8">Sources are available to the internal team.</p></>;
  return <section className="space-y-6 pb-12 text-[#1B2433]">
    <PageTabs label="Sources" tabs={TABS} current={tab} />
    {children}
  </section>;
}

/** `/sources/cycle`: the latest week's cycle panel (budgets, the cycles, how the week went and, for an approver, Run cycle). */
export function WeeklyCycle() {
  const { me } = useMe();
  const weeks = useWeekList();
  return <>
    <PageHeading title="Sources" subtitle="The weekly cycle: what it read, how it went, and running one by hand" />
    {weeks.weeks.isPending ? <LoadingState>Loading the weeks…</LoadingState> : <CyclePanel weekId={weeks.latest} canDecide={me.can.decide} />}
  </>;
}
