import {createRoot} from 'react-dom/client';
import { lazy, Suspense } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import App from './App.tsx';
import './index.css';
import { AuthProvider } from './auth/AuthProvider';
import { AuthGate } from './auth/AuthGate';
import { createQueryClient } from './api/query';

// Vite removes this development-only import and toolbar from production builds.
const DevAgentation = import.meta.env.DEV
  ? lazy(() => import('./components/DevAgentation'))
  : null;

const queryClient = createQueryClient();

createRoot(document.getElementById('root')!).render(
  <>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider><AuthGate><App /></AuthGate></AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
    {DevAgentation && <Suspense fallback={null}><DevAgentation /></Suspense>}
  </>
);
