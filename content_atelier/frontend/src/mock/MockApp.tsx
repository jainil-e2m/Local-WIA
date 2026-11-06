import React from 'react';
import { Link, Route, Routes } from 'react-router-dom';
import { ViewBoundary } from '../components/shared/ViewBoundary';
import MockStudioApp from './App';
import { SampleDataWorkspace } from './SampleDataWorkspace';
import { SAMPLE_VIEWS, type SampleViewEntry } from './sampleViews';

/* The demo build (VITE_ATELIER_MODE=mock, 6.F3): the saved mock flow at every path, and the sample screens at
   /sample/<view>. Nothing here is in the real app's bundle: src/App.tsx imports it only for the demo build. */

function SampleScreen({ view }: { view: SampleViewEntry }) {
  return <main className="min-h-screen bg-[#F6F7FB] text-[#1B2433] font-sans antialiased px-3 sm:px-7 lg:px-10 py-6 space-y-4">
    <Link to="/" className="text-sm underline text-[#173354]">Back to the demo</Link>
    <ViewBoundary name={view.title} resetKey={view.path}><SampleDataWorkspace view={view.sample} /></ViewBoundary>
  </main>;
}

export default function MockApp() {
  return <Routes>
    {SAMPLE_VIEWS.map(view => <Route key={view.id} path={view.path.slice(1)} element={<SampleScreen view={view} />} />)}
    <Route path="*" element={<MockStudioApp />} />
  </Routes>;
}
