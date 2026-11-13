/* NOT RENDERED TODAY — App.tsx composes Header + Hero only, and the hero's
   launcher replaced the footer. Kept because the component is wanted back if
   the landing page ever grows a second screenful, and corrected rather than
   left stale: every name, link and byline below belonged to Wahha Design, the
   dashboard this one was forked from. A footer that reaches the page carrying
   another agency's copyright is the worst kind of leftover. */
const socials = [
  {
    label: "Wedding Industry Ads on Instagram",
    href: "https://www.instagram.com/weddingindustryads/",
    path: "M389.2 48h70.6L305.6 224.2 487 464H345L233.7 318.6 106.5 464H35.8L200.7 275.5 26.8 48H172.4L272.9 180.9 389.2 48zM364.4 421.8h39.1L151.1 88h-42L364.4 421.8z",
    view: "0 0 512 512",
  },
  {
    label: "Wedding Industry Ads on Facebook",
    href: "https://www.facebook.com/weddingindustryads",
    path: "M80 299.3V512H196V299.3h86.5l18-97.8H196V166.9c0-51.7 20.3-71.5 72.7-71.5c16.3 0 29.4 .4 37 1.2V7.9C291.4 4 256.4 0 236.2 0C129.3 0 80 50.5 80 159.4v42.1H14v97.8H80z",
    view: "0 0 320 512",
  },
  {
    label: "Wedding Industry Ads on LinkedIn",
    href: "https://www.linkedin.com/company/weddingindustryads/",
    path: "M100.28 448H7.4V148.9h92.88zM53.79 108.1C24.09 108.1 0 83.5 0 53.8a53.79 53.79 0 0 1 107.58 0c0 29.7-24.1 54.3-53.79 54.3zM447.9 448h-92.68V302.4c0-34.7-.7-79.2-48.29-79.2-48.29 0-55.69 37.7-55.69 76.7V448h-92.78V148.9h89.08v40.8h1.3c12.4-23.5 42.69-48.3 87.88-48.3 94 0 111.28 61.9 111.28 142.3V448z",
    view: "0 0 448 512",
  },
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-ink px-6 pb-14 pt-16 text-white/72">
      <div className="container grid items-center gap-10 text-center md:grid-cols-3 md:text-left">
        <div>
          <img
            src="/logo-white.svg"
            alt="Wedding Industry Ads"
            className="mx-auto mb-4 h-[52px] w-auto md:mx-0"
          />
          <p className="text-sm leading-relaxed text-white/55">
            Paid advertising for wedding venues and pros
            <br />
            Texas
          </p>
        </div>

        <div className="flex justify-center gap-3.5">
          {socials.map((s) => (
            <a
              key={s.href}
              href={s.href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={s.label}
              className="grid h-11 w-11 place-items-center rounded-full border border-white/18 text-white/80 transition-all duration-300 hover:-translate-y-1 hover:border-brand-orange hover:bg-brand-orange hover:text-white"
            >
              <svg viewBox={s.view} className="h-[17px] w-[17px]" fill="currentColor" aria-hidden>
                <path d={s.path} />
              </svg>
            </a>
          ))}
        </div>

        <div className="text-sm md:text-right">
          <p>© {year} Wedding Industry Ads. All rights reserved.</p>
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.25em] text-white/35">
            AI Command Center · built by E2M Solutions
          </p>
        </div>
      </div>
    </footer>
  );
}
