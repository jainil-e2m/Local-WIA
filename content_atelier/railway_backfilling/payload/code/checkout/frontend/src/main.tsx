import {createRoot} from 'react-dom/client';
import { lazy, Suspense } from 'react';
import App from './App.tsx';
import './index.css';
import { AuthProvider } from './auth/AuthProvider';
import { AuthGate } from './auth/AuthGate';

// Vite removes this development-only import and toolbar from production builds.
const DevAgentation = import.meta.env.DEV
  ? lazy(() => import('./components/DevAgentation'))
  : null;

createRoot(document.getElementById('root')!).render(
  <>
    <AuthProvider><AuthGate><App /></AuthGate></AuthProvider>
    {DevAgentation && <Suspense fallback={null}><DevAgentation /></Suspense>}
  </>
);
