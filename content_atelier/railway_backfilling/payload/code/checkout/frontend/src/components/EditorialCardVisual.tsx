import React from 'react';

interface EditorialCardVisualProps {
  type: string;
  title: string;
}

export const EditorialCardVisual: React.FC<EditorialCardVisualProps> = ({ type, title }) => {
  if (type === 'Client Call' || title.includes('Planner')) {
    return (
      <div className="relative w-full h-48 sm:h-52 bg-gradient-to-tr from-[#1E2540] via-[#2D3F75] to-[#5070FF] overflow-hidden flex items-end p-5 img-outline">
        {/* Soft luxury lighting & bokeh elements */}
        <div className="absolute inset-0 opacity-40 bg-[radial-gradient(circle_at_30%_20%,#C5C9DE,transparent_65%)]" />
        <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-[#8DA1FD]/25 blur-2xl pointer-events-none" />
        <div className="absolute top-8 left-10 w-24 h-24 rounded-full bg-[#C39878]/25 blur-xl pointer-events-none" />

        {/* Champagne flutes & celebration sketch silhouette */}
        <div className="absolute right-4 bottom-3 opacity-25">
          <svg width="84" height="110" viewBox="0 0 84 110" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M24 8L34 52C34 60 28 66 20 66C12 66 6 60 6 52L16 8H24Z" stroke="#FFF5EA" strokeWidth="2" strokeMiterlimit="10"/>
            <path d="M20 66V96M10 96H30" stroke="#FFF5EA" strokeWidth="2" strokeLinecap="round"/>
            <path d="M54 20L62 56C62 62 57 67 50 67C43 67 38 62 38 56L46 20H54Z" stroke="#FFF5EA" strokeWidth="2" strokeMiterlimit="10"/>
            <path d="M50 67V96M40 96H60" stroke="#FFF5EA" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="28" cy="22" r="3" fill="#FFE2C9" />
            <circle cx="44" cy="30" r="2" fill="#FFE2C9" />
            <circle cx="20" cy="38" r="2" fill="#FFE2C9" />
          </svg>
        </div>

        {/* Ambient editorial typography watermark */}
        <div className="relative z-10">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#E0DFE2]/90 block font-medium">
            10-Week Case Study · Sarah J.
          </span>
          <span className="font-editorial text-xl italic font-semibold text-white tracking-wide">
            The Organic Hiatus
          </span>
        </div>
      </div>
    );
  }

  if (type === 'Industry Trend' || title.includes('Trends')) {
    return (
      <div className="relative w-full h-48 sm:h-52 bg-gradient-to-tr from-[#1E2530] via-[#354854] to-[#5070FF]/90 overflow-hidden flex items-end p-5 img-outline">
        {/* Soft floral garden ambient lighting */}
        <div className="absolute inset-0 opacity-35 bg-[radial-gradient(circle_at_70%_30%,#EDF3FA,transparent_55%)]" />
        <div className="absolute -top-10 -left-10 w-40 h-40 rounded-full bg-[#8DA1FD]/25 blur-2xl" />

        {/* Floral arch motif */}
        <div className="absolute right-4 bottom-2 opacity-30">
          <svg width="100" height="110" viewBox="0 0 100 110" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 105C10 50 30 15 50 15C70 15 90 50 90 105" stroke="#F4FAF5" strokeWidth="2.5" strokeDasharray="4 4"/>
            <circle cx="30" cy="35" r="8" fill="#F4FAF5" fillOpacity="0.4" />
            <circle cx="70" cy="35" r="8" fill="#F4FAF5" fillOpacity="0.4" />
            <circle cx="50" cy="18" r="10" fill="#F4FAF5" fillOpacity="0.5" />
            <path d="M42 22C46 14 54 14 58 22" stroke="#F4FAF5" strokeWidth="2"/>
          </svg>
        </div>

        <div className="relative z-10">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#C5C9DE]/90 block font-medium">
            SerpAPI Trend Surge · 2026
          </span>
          <span className="font-editorial text-xl italic font-semibold text-white tracking-wide">
            Multi-Day Luxury Weekends
          </span>
        </div>
      </div>
    );
  }

  if (type === 'Client Story' || title.includes('Inquiries')) {
    return (
      <div className="relative w-full h-48 sm:h-52 bg-gradient-to-tr from-[#221E17] via-[#4B4137] to-[#C39878] overflow-hidden flex items-end p-5 img-outline">
        {/* Modern studio moodboard ambient */}
        <div className="absolute inset-0 opacity-35 bg-[radial-gradient(circle_at_30%_30%,#FDF9F5,transparent_50%)]" />
        <div className="absolute -bottom-8 -right-8 w-36 h-36 rounded-full bg-[#8DA1FD]/20 blur-xl" />

        {/* Lead conversion graph & envelope graphic */}
        <div className="absolute right-4 bottom-3 opacity-30">
          <svg width="90" height="90" viewBox="0 0 90 90" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="15" y="25" width="60" height="42" rx="4" stroke="#FAF8FF" strokeWidth="2"/>
            <path d="M15 30L45 52L75 30" stroke="#FAF8FF" strokeWidth="2" strokeLinecap="round"/>
            <path d="M22 18L35 8L48 14L68 5" stroke="#F0E8FF" strokeWidth="2.5" strokeLinecap="round"/>
            <circle cx="68" cy="5" r="3" fill="#FFF" />
          </svg>
        </div>

        <div className="relative z-10">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#F1EDFF]/90 block font-medium">
            LeadLock Architecture
          </span>
          <span className="font-editorial text-xl italic font-semibold text-white tracking-wide">
            Rapid Conversion Engine
          </span>
        </div>
      </div>
    );
  }

  // Default Vault Workshop / Advisory styling
  return (
    <div className="relative w-full h-48 sm:h-52 bg-gradient-to-tr from-[#221E17] via-[#3E342B] to-[#5070FF]/70 overflow-hidden flex items-end p-5 img-outline">
      <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_50%_20%,#FFF6ED,transparent_60%)]" />
      <div className="relative z-10">
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#E0DFE2]/90 block font-medium">
          Vault Masterclass · Offers
        </span>
        <span className="font-editorial text-xl italic font-semibold text-white tracking-wide">
          High-Ticket Positioning
        </span>
      </div>
    </div>
  );
};

