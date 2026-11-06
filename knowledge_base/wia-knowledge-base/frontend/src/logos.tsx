import type { ReactNode } from 'react';

/*
 * Client logos for the portfolio cards. All logos here are fictional, drawn for the preview.
 *
 * Intended extraction (approved sources only; website scraping is outside current intake):
 *   1. Drive brand folder: the logo file the client shares at onboarding (svg/png preferred).
 *   2. Gmail: the logo image in the primary contact's email signature.
 *   3. Nothing found: initials on a neutral tint, flagged "Logo pending".
 * The card background is a light tint of the logo's main colour, so every card stays readable.
 * A person can replace the extracted logo; the source and date are kept for traceability.
 */

/** `userScale` is the display size chosen in the client editor (1 = as extracted or uploaded). */
export interface ClientLogo { mark: ReactNode; tint: string; source: 'Drive · Brand folder' | 'Gmail · email signature' | 'Uploaded in the KB'; file: string; extracted: string; userScale?: number }

const serif = "'Playfair Display', Georgia, serif";
const sans = "'Poppins', system-ui, sans-serif";

export const LOGOS: Record<string, ClientLogo | undefined> = {
  bloom: {
    tint: '#eef1e6', source: 'Drive · Brand folder', file: 'Bloom Manor / Brand / logo-primary.svg', extracted: '2026-04-08',
    mark: <svg viewBox="0 0 200 80" role="img" aria-label="Bloom Manor logo">
      <g fill="none" stroke="#5f6d45" strokeWidth="1.6" strokeLinecap="round">
        <path d="M100 8v20" /><path d="M100 18c-6-6-12-6-15-3 3 3 9 3 15 3z" fill="#5f6d45" fillOpacity=".18" /><path d="M100 14c6-6 12-6 15-3-3 3-9 3-15 3z" fill="#5f6d45" fillOpacity=".18" /><circle cx="100" cy="7" r="2.4" fill="#5f6d45" stroke="none" />
      </g>
      <text x="100" y="52" textAnchor="middle" fontFamily={serif} fontSize="19" letterSpacing="4" fill="#4b5737">BLOOM MANOR</text>
      <text x="100" y="68" textAnchor="middle" fontFamily={sans} fontSize="7" letterSpacing="3.5" fill="#7d8964">HILL COUNTRY · EST. 2014</text>
    </svg>,
  },
  rosewood: {
    tint: '#f6ecea', source: 'Drive · Brand folder', file: 'Rosewood Estate / Brand / rosewood-mark.png', extracted: '2026-02-14',
    mark: <svg viewBox="0 0 200 80" role="img" aria-label="Rosewood Estate logo">
      <g fill="none" stroke="#8b4a4f" strokeWidth="1.5"><circle cx="40" cy="40" r="17" /><path d="M40 30c5 0 8 4 8 9s-4 8-8 8-8-3-8-8 3-9 8-9z" /><path d="M36 37c2-3 6-3 8 0M35 42c3 2 7 2 10 0" /></g>
      <text x="68" y="42" fontFamily={serif} fontStyle="italic" fontSize="25" fill="#7a3c42">Rosewood</text>
      <text x="69" y="58" fontFamily={sans} fontSize="8" letterSpacing="4.2" fill="#a0676b">ESTATE</text>
    </svg>,
  },
  willow: {
    tint: '#e7efeb', source: 'Gmail · email signature', file: 'Maya Stone · signature image (Sep 24 email)', extracted: '2026-07-16',
    mark: <svg viewBox="0 0 200 80" role="img" aria-label="Willow & Pine logo">
      <path d="M100 6l-11 17h6l-9 13h9l-8 12h26l-8-12h9l-9-13h6z" fill="#2f5245" />
      <rect x="98.5" y="48" width="3" height="6" fill="#2f5245" />
      <text x="100" y="72" textAnchor="middle" fontFamily={sans} fontWeight="600" fontSize="12" letterSpacing="3" fill="#2f5245">WILLOW &amp; PINE</text>
    </svg>,
  },
  everly: {
    tint: '#efeeec', source: 'Drive · Brand folder', file: 'Everly Films / Brand / everly-wordmark.svg', extracted: '2026-05-20',
    mark: <svg viewBox="0 0 200 80" role="img" aria-label="Everly Films logo">
      <circle cx="44" cy="40" r="15" fill="none" stroke="#2b2b2b" strokeWidth="1.6" /><path d="M40 33v14l11-7z" fill="#2b2b2b" />
      <text x="70" y="45" fontFamily={sans} fontWeight="300" fontSize="22" letterSpacing="1" fill="#2b2b2b">everly</text>
      <text x="139" y="45" fontFamily={sans} fontWeight="600" fontSize="22" fill="#2b2b2b">films</text>
    </svg>,
  },
  // Harbor House is onboarding and hasn't shared brand files yet: the card shows the fallback.
  harbor: undefined,
  magnolia: {
    tint: '#f8eee8', source: 'Drive · Brand folder', file: 'Magnolia Events / Brand / magnolia-logo.svg', extracted: '2026-08-22',
    mark: <svg viewBox="0 0 200 80" role="img" aria-label="Magnolia Events logo">
      <g fill="#b0705b" fillOpacity=".2" stroke="#b0705b" strokeWidth="1.3"><path d="M100 30c-6-8-6-17 0-24 6 7 6 16 0 24z" /><path d="M99 30c-9-3-14-10-14-18 9 1 14 9 14 18z" /><path d="M101 30c9-3 14-10 14-18-9 1-14 9-14 18z" /></g>
      <text x="100" y="56" textAnchor="middle" fontFamily={serif} fontSize="22" fill="#94573f">Magnolia</text>
      <text x="100" y="70" textAnchor="middle" fontFamily={sans} fontSize="7.5" letterSpacing="5" fill="#b0705b">EVENTS</text>
    </svg>,
  },
};
