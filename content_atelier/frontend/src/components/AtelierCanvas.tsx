import React from 'react';

interface AtelierCanvasProps {
  className?: string;
}

/**
 * Luxury Wedding Industry Ads ambient atmosphere.
 * Completely free of any wave meshes or undulating canvas geometry.
 * Employs subtle champagne gold, royal cobalt, and pearl diffuse lighting
 * reminiscent of a high-end luxury bridal design studio.
 */
export const AtelierCanvas: React.FC<AtelierCanvasProps> = ({ className = '' }) => {
  return (
    <div
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {/* Base warm porcelain / alabaster backdrop */}
      <div className="absolute inset-0 bg-[#F6F7FB]" />

      {/* Top-Right: Warm Champagne Gold Ambient Aura */}
      <div
        className="absolute -top-32 right-[-10%] w-[650px] h-[650px] rounded-full blur-[140px] opacity-30"
        style={{
          background: 'radial-gradient(circle, rgba(195, 152, 120, 0.16) 0%, rgba(230, 203, 179, 0.08) 50%, transparent 75%)',
        }}
      />

      {/* Bottom-Left: Subtle Royal Cobalt / Iris Glow */}
      <div
        className="absolute -bottom-40 left-[-8%] w-[700px] h-[700px] rounded-full blur-[160px] opacity-25"
        style={{
          background: 'radial-gradient(circle, rgba(80, 112, 255, 0.10) 0%, rgba(141, 161, 253, 0.05) 50%, transparent 75%)',
        }}
      />

      {/* Center-Top: Luminous Bridal Pearl Lighting */}
      <div
        className="absolute top-[18%] left-[45%] -translate-x-1/2 w-[500px] h-[350px] rounded-full blur-[130px] opacity-40"
        style={{
          background: 'radial-gradient(ellipse, rgba(255, 255, 255, 0.8) 0%, rgba(240, 235, 227, 0.2) 60%, transparent 80%)',
        }}
      />

      {/* Delicate stationary starlight points (high-fashion editorial finish) */}
      <svg
        className="absolute inset-0 w-full h-full opacity-35"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="sparkle-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#C39878" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#C39878" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Subtle, non-intrusive ambient starlight accents */}
        <circle cx="15%" cy="22%" r="1.5" fill="url(#sparkle-grad)" />
        <circle cx="48%" cy="12%" r="1" fill="#8DA1FD" opacity="0.6" />
        <circle cx="82%" cy="28%" r="1.5" fill="url(#sparkle-grad)" />
        <circle cx="75%" cy="68%" r="1" fill="#C39878" opacity="0.4" />
        <circle cx="28%" cy="85%" r="1.5" fill="#8DA1FD" opacity="0.5" />
        <circle cx="90%" cy="82%" r="1" fill="url(#sparkle-grad)" />
      </svg>
    </div>
  );
};
