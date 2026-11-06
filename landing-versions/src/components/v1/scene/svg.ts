/** Catmull–Rom spline through `pts`, as an SVG path of cubic Béziers. */
export function smooth(pts: [number, number][], closed = false, tension = 0.5): string {
  if (pts.length < 2) return "";
  const p = closed ? [pts[pts.length - 1], ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts[pts.length - 1]];
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  const k = tension / 3;
  for (let i = 1; i < p.length - 2; i++) {
    const [x0, y0] = p[i - 1];
    const [x1, y1] = p[i];
    const [x2, y2] = p[i + 1];
    const [x3, y3] = p[i + 2];
    const c1x = x1 + (x2 - x0) * k;
    const c1y = y1 + (y2 - y0) * k;
    const c2x = x2 - (x3 - x1) * k;
    const c2y = y2 - (y3 - y1) * k;
    d += ` C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
  }
  return closed ? `${d} Z` : d;
}

/** Linear interpolation of x along a polyline that is monotonic in y. */
export function xAt(pts: [number, number][], y: number): number {
  if (y <= pts[0][1]) return pts[0][0];
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1];
    const [x1, y1] = pts[i];
    if (y <= y1) return x0 + ((x1 - x0) * (y - y0)) / Math.max(1e-6, y1 - y0);
  }
  return pts[pts.length - 1][0];
}
