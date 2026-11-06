import React from 'react';
import { useAuth } from './AuthProvider';
import { commandCenterLoginUrl } from './session';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status, error, refresh } = useAuth();
  if (status === 'authenticated') return <>{children}</>;
  return (
    <main className="min-h-screen bg-[#F6F7FB] flex items-center justify-center p-6 text-[#173354]">
      <div className="w-full max-w-md rounded-3xl bg-white border border-[#E8EBF1] p-10">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#A88A52]">Wedding Industry Ads</p>
        <h1 className="font-editorial text-3xl mt-4">Content Atelier</h1>
        <p role="status" className="mt-4 text-sm text-[#667184] leading-relaxed">
          {status === 'loading' ? 'Checking your session…' : status === 'error' ? error : 'Sign in with your Command Center account to open your editorial workspace.'}
        </p>
        {status === 'unauthenticated' && <a href={commandCenterLoginUrl()} className="block mt-6 rounded-xl bg-[#173354] px-4 py-3 text-center text-sm text-white">Sign in</a>}
        {status === 'error' && <button type="button" onClick={() => void refresh()} className="mt-6 w-full rounded-xl bg-[#173354] px-4 py-3 text-sm text-white">Retry connection</button>}
      </div>
    </main>
  );
}
