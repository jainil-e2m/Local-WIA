import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ViewBoundary } from '../components/shared/ViewBoundary';
import { LoadingState } from '../components/shared/states';
import { useFeatureFlagState, type FeatureFlags } from '../utils/workspace';
import { paths } from './routes';

/** A view inside its own error boundary. The boundary clears when the path changes, so leaving a failed view and coming back retries it. */
export function Page({ name, children }: { name: string; children: React.ReactNode }) {
  const { pathname } = useLocation();
  return <ViewBoundary name={name} resetKey={pathname}>{children}</ViewBoundary>;
}

export function NotAvailable({ what }: { what: string }) {
  return <section role="status" className="py-10 max-w-xl space-y-3">
    <h1 className="font-editorial text-3xl text-[#173354]">{what} is not available</h1>
    <p className="text-sm text-slate-600">This part of Content Atelier is switched off, or is not open to your account.</p>
    <Link to={paths.studio} className="underline text-sm">Go to the Weekly Studio</Link>
  </section>;
}

/** Shows its children only when the feature flags allow it. A deep link waits for the flags instead of being sent away on the default. */
export function FlagGate({ allow, what, children }: { allow: (flags: FeatureFlags) => boolean; what: string; children: React.ReactNode }) {
  const { flags, loaded } = useFeatureFlagState();
  if (!loaded) return <LoadingState>Loading…</LoadingState>;
  return allow(flags) ? <>{children}</> : <NotAvailable what={what} />;
}
