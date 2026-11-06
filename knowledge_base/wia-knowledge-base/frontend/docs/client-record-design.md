# Client record cover redesign

The reference works because three layers have distinct jobs: the photographic cover establishes client identity; the bordered utility strip holds dates and source shortcuts; icon-led navigation introduces the working record. The redesign follows those layers without embedding client information in a background image.

## Visual decisions

- Warm ivory photography, soft daylight, restrained navy serif headings, and blue utility icons reproduce the reference's quiet architectural feel. The default vase-and-arch composition was generated specifically for this layout.
- A circular monogram anchors the client name. Category, location, aliases, service, lifecycle, and owner remain actual record fields. Names wrap rather than truncate.
- Health has a separate opaque reading surface, a semantic state color, and its existing destination. The call action opens the client's actual next call; clients without an upcoming call get “View meetings.”
- A fixed light gradient protects the identity text across all covers. Imagery is decorative, with empty alternative text; no record facts depend on image loading.
- The cover is full width within the existing workspace. Responsive container rules also work when the sidebar is expanded or collapsed. On small screens, the health action moves below the identity, dates stack, and record tabs scroll within their own row.
- The existing tabs, counts, finance access rules, and accelerator-specific attendance tab remain driven by the shared client data.

## Cover library and editing

The top-right pencil opens a native accessible dialog with 12 covers, category filters, an unsaved preview, source links, default reset, Cancel, and Save. Escape and outside dismissal discard unsaved selections; focus returns to the pencil.

Eleven stock photographs are downloaded locally in `public/covers/`, with original image and license URLs in `public/covers/sources.json`. Run `node scripts/download-client-covers.mjs` to re-download them. The twelfth is the generated `olive-arch.png`. Cover IDs and image focal positions live in `src/clientCovers.ts`. Keep IDs stable when replacing files. For new assets, use literal image paths so the single-file exporter can embed them.

All 12 images and the fonts are embedded in `exports/client-portfolio.html`. There are no runtime stock-photo requests. The larger (~13 MB) file is intentional for offline review. A hosted build serves separate cacheable files and only loads the selected hero until the library opens.

## Image sources

- [Pexels](https://www.pexels.com/search/minimalist%20vase/) — the included stock library; [license](https://www.pexels.com/license/).
- [Unsplash](https://unsplash.com/s/photos/minimal-interior) — an additional place to curate interior images; check each photo's Free / Unsplash+ label and its applicable license before downloading.
- [Kaboompics](https://kaboompics.com/photo/26005/concept-photos-flowers-vase-minimalist-interior) — coordinated still-life series with matching palettes and alternate crops.

Useful searches: “minimalist vase,” “olive branch ceramic vase,” “Mediterranean arch interior,” “sunlight plaster wall,” “linen curtain shadows.” Prefer landscape compositions, quiet left-hand space, warm neutrals, and no people, lettering, or logos. Original images can be replaced with more tightly art-directed wide photographs over time; some included stock alternatives are cropped from portrait originals.

## Live integration contract

The same `ClientDetail` component renders both sample records and the real KB snapshot (`npm run export:wia`). There are no Bloom-specific branches. `Client.coverId?: string` accepts a stable library ID; an omitted or unknown ID uses `olive-arch`.

In this HTML preview, Save writes `wia-client-cover-v1:<clientId>` in this browser's local storage. It survives reloads and stays independent for each client. Blocked storage falls back to the current session with an explicit notice. This is a local preference, not a shared server update.

For team-wide persistence, add `coverId` to the client settings stored by the backend and returned by the client API/snapshot, then replace the local save adapter with that authenticated update endpoint. Do not store image bytes on individual client records: store the stable cover ID and serve the shared library from the app's static assets or CDN. Apply the application's existing authorization to that endpoint. The current UI does not add a backend write API.

## Generated asset provenance

Created using the built-in OpenAI ImageGen tool. Final saved asset: `public/covers/olive-arch.png`.

Prompt: “Use case: photorealistic-natural. Asset type: wide decorative background for a sophisticated wedding industry client record header. Create one cinematic ultra-wide editorial interior photograph, aspect ratio about 3:1. Warm ivory limewashed plaster wall, one elegant tall rounded recessed arch right of center, matte white ceramic vase with airy olive branches beneath the arch. Gentle afternoon sunlight from upper left, organic soft foliage shadows, realistic plaster texture, cream limestone, quiet upscale Mediterranean architecture. The entire LEFT 45 percent must be almost empty very light ivory wall with subtle light and enough negative space for navy interface text. Vase and foliage around 65 percent across the composition. The RIGHT 18 percent light quiet wall for a card overlay. Refined desaturated warm neutrals, pale sage foliage. No text, no interface, no logos, no border, no people. A single wide photograph, not a collage.”
