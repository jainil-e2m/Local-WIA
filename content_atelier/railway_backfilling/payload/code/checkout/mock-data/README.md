# Weekly Studio mock replay

Open Weekly Studio and use the “Fathom mock week · Replay the workflow” controls.

- **Start at angles:** review each concept and approve it to open its saved brief.
- **Preview briefs:** show all four complete briefs awaiting approval.
- **Preview packs:** show the four matching packs, each with an email, eight-slide carousel, three spoken reel scripts, and captions.
- **Ready to schedule:** show all four packs in the scheduling queue; use the normal date and time picker.
- **Preview scheduled:** show future sample dates, starting tomorrow at 10:00 AM IST and spreading the four packs over consecutive days.

You can also step through one concept using the normal approval buttons. Source analysis and briefs remain linked through every stage. Replays preserve titles, editorial edits, and the rest of the library while replacing these four mocks’ progress. Browser reloads retain the chosen state.

The JSON file is a saved export of the four default records, including their analysis, evidence, production briefs, and pack templates. It contains no live publishing action. The application uses the matching TypeScript mock data.

Validation: 103 frontend tests pass, TypeScript checking passes, and the production build succeeds. Tests cover every preview, manual progression, saved-data migration, IST scheduling, and twenty linked calendar pieces.
