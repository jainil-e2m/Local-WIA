// '@finance-live' is real GHL data in the local live export and an empty stub elsewhere (see vite.config.ts).
declare module '@dubsado-live' {
  const data: import('./financeLive').DubsadoRaw;
  export default data;
}
// '@kb-live' is the KB portfolio: a local snapshot (export:wia), filled at start in production (build:live), {} elsewhere.
declare module '@kb-live' {
  const data: import('./kbLive').KbLive;
  export default data;
}
declare module '@finance-live' {
  const data: import('./financeLive').LiveRaw;
  export default data;
}
