/* A tiny signal line from the copy column to the scene. Hovering "Enter
   Command Center" wakes the laptop, so the button and the object it stands
   for answer each other. Module-level because there is only ever one scene. */

type Listener = () => void;

const wakeListeners = new Set<Listener>();

export function onLaptopWake(fn: Listener) {
  wakeListeners.add(fn);
  return () => {
    wakeListeners.delete(fn);
  };
}

export function wakeLaptop() {
  wakeListeners.forEach((fn) => fn());
}
