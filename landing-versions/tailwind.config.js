import tailwindcssAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    /* ONE WIDTH SYSTEM FOR EVERY PAGE.
       `.container` is the app's only page shell: full-bleed with stepped
       gutters until it hits the ceiling below, then centred. Every route uses
       it, so no page can drift to its own hand-picked width.

       WHY A CEILING AT ALL. Uncapped, a 2560px display would run table rows
       and prose to ~2500px, where the eye loses the row on the way across and
       a paragraph exceeds any readable measure. The cap is the ergonomic
       limit, not a layout shortcut; blocks of prose carry their own tighter
       `max-w-*` on top of it.

       Note `screens` here is Tailwind's container map, where each value is used
       as BOTH the media min-width and the max-width — so this reads "below
       1600 be fluid, at or above it stop at 1600".

       WHY 1600 AND NOT 1920. It was 1920 for exactly one release, on the
       reasoning that 1600 wastes 160px each side of a 24" monitor. That
       ceiling never engaged. Because the value is a media MIN-WIDTH, a 1920
       cap only applies from 1920px up, and a maximised window on a 1920
       monitor never reports 1920 CSS px — the scrollbar takes it to ~1903, and
       this hero measured 1919. So every large screen fell through to
       full-bleed: the logo sat 48px off the window edge, the hero copy and its
       asset drifted to the far corners, and the KPI row stretched to 1157px
       with the figures too far apart to read as one row.

       The lesson is the general one, so do not re-raise this: a ceiling keyed
       to a min-width media query does nothing unless it sits BELOW the widths
       people actually browse at. 1600 engages on every desktop from a 13"
       laptop up, which is the point of having it.

       THE GUTTER IS A CLAMP, NOT BREAKPOINT STEPS, AND THAT IS FORCED.
       Overriding `container.screens` means Tailwind emits container media
       queries for THOSE keys only — so a breakpoint-keyed `padding` map
       (sm/lg/xl/2xl) is silently dropped, leaving one 1rem gutter all the way
       up. Verified by reading the served CSS: only the base rule and the
       ceiling rule survived. `clamp()` sidesteps the whole mechanism and is
       better anyway: 24px at an 11" tablet, ~38px on a 13" laptop, 48px from
       1600 up, interpolating rather than jumping. At and above the ceiling the
       gutter is inside the 1600, so the measure is 1504. */
    container: {
      center: true,
      padding: "clamp(1rem, 3vw, 3rem)",
      screens: { "2xl": "1600px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        /* Wedding Industry Ads brand palette. Every value below comes from
           the weddingindustryads.com extraction (design spec, 2026-09-07) --
           nothing here is invented, per that spec's own rule.

           The hub's original key names are kept and repointed so every
           existing `brand-*` class still resolves. Two names no longer
           describe their value and survive only for compatibility:
           `orange` is now the brand's camel, `teal` its mocha. */
        brand: {
          primary: "#5070ff", // CTAs, links, focus, emphasis
          secondary: "#4b4137", // sub-headings and muted body copy
          accent: "#221e17", // strongest ink; headline end-stop
          orange: "#c39878", // camel -- the warm accent (was orange)
          teal: "#87725f", // mocha -- second warm (was teal)
          sky: "#8da1fd", // light periwinkle
          lavender: "#c5c9de", // light blue-grey
          ink: "#221e17", // warm near-black
          surface: "#fefefe", // off-white panel fill

          /* Light-theme neutrals the flip needs, same extraction. */
          mist: "#e0dfe2", // hairlines and soft dividers
          stone: "#c7beb2", // warm light grey -- hover borders
          slate: "#9da2b1", // decorative icon tint only (2.5:1 on white)
          gray: "#6d6e6d", // tertiary text -- 5.05:1 on white
        },

        /* Lead Magnet console — the one surface in the hub that runs light
           frosted panels on the dark ground.

           Text on those panels uses the brand palette directly, not values
           invented here: brand.primary reads 8.44:1 on the panel and
           brand.secondary 5.31:1, so the page stays on-theme and clears AA
           without a parallel ink ramp. (brand.accent is 3.25:1 — large text
           only — so it is deliberately not used for body copy.)

           Only what the brand palette cannot express lives here: a hairline
           rule, and semantic score colours. brand.orange/teal/sky all fall
           under 1.7:1 on near-white, so the status hues need darker ends. */
        console: {
          rule: "#dfe3ec",
          good: "#16724c",
          "good-dot": "#1f9d63",
          bad: "#a83323",
          "bad-dot": "#dd4630",
          warn: "#7d4a0f",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 5px)",
        sm: "calc(var(--radius) - 9px)",
      },
      keyframes: {
        marquee: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-33.333%)" },
        },
        shimmer: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-16px)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(80,112,255,0.45)" },
          "70%": { boxShadow: "0 0 0 9px rgba(80,112,255,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(80,112,255,0)" },
        },
        "bounce-subtle": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(8px)" },
        },
        /* Opacity only — deliberately never touches `transform`. Elements whose
           position comes from a transform (tooltips use translate() to offset
           from their anchor) would otherwise be dragged in from the wrong spot,
           because an animated transform overrides the positioning one. */
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
      },
      animation: {
        marquee: "marquee 32s linear infinite",
        shimmer: "shimmer 6s ease-in-out infinite",
        float: "float 7s ease-in-out infinite",
        "spin-slow": "spin-slow 26s linear infinite",
        "pulse-ring": "pulse-ring 2.4s ease-in-out infinite",
        "bounce-subtle": "bounce-subtle 2s ease-in-out infinite",
        "fade-in": "fade-in 120ms ease-out",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};
