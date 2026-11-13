/** Time-of-day greeting for the landing hero, from the viewer's local clock. */
export function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}
