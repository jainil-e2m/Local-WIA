import { after } from 'node:test';
import { JSDOM } from 'jsdom';

/* Installs a browser's globals. Import this module before anything that imports react-dom: React decides at load time
   whether it is in a browser (`canUseDOM`), so the globals must exist first. */

let installed: JSDOM | null = null;

export function installDom(url = 'http://localhost/') {
  if (installed) return installed;
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url, pretendToBeVisual: true });
  const { window } = dom;
  const globals: Record<string, unknown> = {
    window, document: window.document, navigator: window.navigator, HTMLElement: window.HTMLElement, Element: window.Element, Node: window.Node,
    Event: window.Event, MouseEvent: window.MouseEvent, KeyboardEvent: window.KeyboardEvent, getComputedStyle: window.getComputedStyle.bind(window),
    requestAnimationFrame: window.requestAnimationFrame.bind(window), cancelAnimationFrame: window.cancelAnimationFrame.bind(window),
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
    localStorage: window.localStorage, sessionStorage: window.sessionStorage,
    ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
  };
  // The DOM's own classes (Window, HTMLInputElement, MutationObserver, ...), so `instanceof` checks in libraries see the same ones.
  for (const name of Object.getOwnPropertyNames(window)) {
    if (/^(Window|HTML\w*Element|DocumentFragment|Document|Text|Comment|CustomEvent|MutationObserver|DOMException|FormData|SVG\w*Element)$/.test(name)) globals[name] = (window as unknown as Record<string, unknown>)[name];
  }
  for (const [name, value] of Object.entries(globals)) Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
  Object.defineProperty(window, 'matchMedia', { value: globals.matchMedia, configurable: true });
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  installed = dom;
  return dom;
}


installDom();
// jsdom keeps timers running for its animation frames; close the window when the file's tests are done so the process can exit.
after(() => { installed?.window.close(); });
