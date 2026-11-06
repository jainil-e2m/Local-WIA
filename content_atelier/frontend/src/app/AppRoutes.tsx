import React from 'react';
import { Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { BackendStudio } from '../components/BackendStudio';
import { ContentPacks } from '../components/ContentPacks';
import { SQLWeeklyAngles } from '../components/SQLWeeklyAngles';
import { SQLBriefs } from '../components/SQLBriefs';
import { PreviousConcepts } from '../components/PreviousConcepts';
import { ScheduledStep } from '../components/studio/ScheduledStep';
import { SourcesView, WeeklyCycle } from '../components/SourcesView';
import { DocumentView } from '../components/DocumentsView';
import { DocumentsOverview } from '../components/ExtractionHealth';
import { MomentView } from '../components/MomentDetail';
import { MomentsShell, MomentsView } from '../components/MomentsLedger';
import { IntakeView } from '../components/IntakeView';
import { AlertsAndCosts } from '../components/AlertsAndCosts';
import { KnowledgePage } from '../components/KnowledgePage';
import { SettingsView } from '../components/SettingsView';
import { LoadingState } from '../components/shared/states';
import { useFeatureFlagState } from '../utils/workspace';
import { AppShell } from './AppShell';
import { HomePage } from './HomePage';
import { FlagGate, NotAvailable, Page } from './Page';
import { paths } from './routes';

function Studio() {
  const { flags, loaded } = useFeatureFlagState();
  if (!loaded) return <LoadingState>Loading…</LoadingState>;
  return <BackendStudio flags={flags} />;
}

/** The calendar keeps its filters in the query string, so an alias path keeps them too. */
function CalendarAlias() {
  const { search } = useLocation();
  return <Navigate to={`${paths.home}${search}`} replace />;
}

function KnowledgeGate({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  return <FlagGate allow={flags => flags.context && user?.role === 'team'} what="Knowledge">{children}</FlagGate>;
}

/** An earlier link to a scheduled pack opens the pack itself. */
function ScheduledPack() {
  const { packId = '' } = useParams();
  return <Navigate to={paths.studioPack(packId)} replace />;
}

const PACKS = (flags: { packs: boolean }) => flags.packs;

/** Every path of the app. A view that is not switched on answers with a notice at its own path rather than sending the
    person elsewhere, so a deep link to it stays honest. The sample screens (/sample/*) are in the demo build only (6.F3). */
export function AppRoutes() {
  return <Routes>
    <Route element={<AppShell />}>
      {/* The app opens on Home, as the 20 October mockup does. */}
      <Route index element={<Navigate to={paths.home} replace />} />
      <Route path="home" element={<Page name="Home"><HomePage /></Page>} />
      <Route path="calendar" element={<CalendarAlias />} />

      <Route path="studio" element={<Studio />}>
        <Route index element={<Navigate to="angles" replace />} />
        <Route path="angles" element={<Page name="Content angles"><SQLWeeklyAngles /></Page>} />
        <Route path="angles/:weekId" element={<Page name="Content angles"><SQLWeeklyAngles /></Page>} />
        <Route path="angles/:weekId/:angleId" element={<Page name="Content angles"><SQLWeeklyAngles /></Page>} />
        <Route path="briefs" element={<Page name="Content briefs"><SQLBriefs /></Page>} />
        <Route path="briefs/:briefId" element={<Page name="Content briefs"><SQLBriefs /></Page>} />
        <Route path="packs" element={<Page name="Content packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.studioPacks} /></FlagGate></Page>} />
        <Route path="packs/:packId" element={<Page name="Content packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.studioPacks} /></FlagGate></Page>} />
        <Route path="packs/week/:weekId" element={<Page name="Content packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.studioPacks} /></FlagGate></Page>} />
        <Route path="scheduled" element={<Page name="Scheduled content"><FlagGate allow={PACKS} what="Scheduled content"><ScheduledStep /></FlagGate></Page>} />
        <Route path="scheduled/:packId" element={<Page name="Scheduled content"><FlagGate allow={PACKS} what="Scheduled content"><ScheduledPack /></FlagGate></Page>} />
      </Route>

      <Route path="previous" element={<Page name="Previous Concepts"><PreviousConcepts /></Page>} />

      <Route path="packs" element={<Page name="Content Packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.packs} /></FlagGate></Page>} />
      <Route path="packs/:packId" element={<Page name="Content Packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.packs} /></FlagGate></Page>} />
      <Route path="packs/week/:weekId" element={<Page name="Content Packs"><FlagGate allow={PACKS} what="Content packs"><ContentPacks base={paths.packs} /></FlagGate></Page>} />

      <Route path="sources" element={<Navigate to={paths.documents} replace />} />
      <Route path="sources/documents" element={<Page name="Sources"><SourcesView tab="documents"><DocumentsOverview /></SourcesView></Page>} />
      <Route path="sources/documents/:transcriptId" element={<Page name="The document"><SourcesView tab="documents"><DocumentView /></SourcesView></Page>} />
      <Route path="sources/intake" element={<Page name="Intake"><SourcesView tab="intake"><IntakeView /></SourcesView></Page>} />
      <Route path="sources/intake/sources/:sourceId" element={<Page name="Intake"><SourcesView tab="intake"><IntakeView /></SourcesView></Page>} />
      <Route path="sources/intake/buckets/:bucketId" element={<Page name="Intake"><SourcesView tab="intake"><IntakeView /></SourcesView></Page>} />
      <Route path="sources/cycle" element={<Page name="Weekly cycle"><SourcesView tab="cycle"><WeeklyCycle /></SourcesView></Page>} />
      <Route path="sources/alerts" element={<Page name="Alerts and costs"><SourcesView tab="alerts"><AlertsAndCosts /></SourcesView></Page>} />

      <Route path="moments" element={<Page name="Moments"><MomentsShell><MomentsView /></MomentsShell></Page>} />
      <Route path="moments/:momentId" element={<Page name="The moment"><MomentsShell><MomentView /></MomentsShell></Page>} />

      <Route path="knowledge" element={<Navigate to={paths.review} replace />} />
      <Route path="knowledge/review" element={<Page name="Knowledge"><KnowledgeGate><KnowledgePage tab="review" /></KnowledgeGate></Page>} />
      <Route path="knowledge/known" element={<Page name="Knowledge"><KnowledgeGate><KnowledgePage tab="known" /></KnowledgeGate></Page>} />
      <Route path="knowledge/known/items/:itemId" element={<Page name="Knowledge"><KnowledgeGate><KnowledgePage tab="known" /></KnowledgeGate></Page>} />
      <Route path="knowledge/versions" element={<Page name="Knowledge"><KnowledgeGate><KnowledgePage tab="versions" /></KnowledgeGate></Page>} />
      <Route path="knowledge/versions/:version" element={<Page name="Knowledge"><KnowledgeGate><KnowledgePage tab="versions" /></KnowledgeGate></Page>} />

      <Route path="settings" element={<Page name="Settings"><SettingsView /></Page>} />

      <Route path="*" element={<NotAvailable what="This page" />} />
    </Route>
  </Routes>;
}
