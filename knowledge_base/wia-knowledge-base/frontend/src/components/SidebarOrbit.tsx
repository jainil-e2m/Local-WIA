import { useEffect, useRef } from 'react';

/** The Content Atelier perimeter light, matched to the KB's blue artwork. */
export default function SidebarOrbit() {
  const ref = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const element = ref.current;
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!element || !canvas || !context) return;

    const padding = 16;
    const sampleCount = 1024;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const mobile = window.matchMedia('(max-width: 700px)');
    let points: { x: number; y: number }[] = [];
    let perimeter = 1;
    let frameId = 0;
    let startedAt: number | null = null;
    let width = 0;
    let height = 0;

    const resize = () => {
      const rect = element.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width + padding * 2;
      height = rect.height + padding * 2;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, padding * ratio, padding * ratio);
      const corners = getComputedStyle(element.parentElement!);
      const left = parseFloat(corners.borderTopLeftRadius) || 0;
      const right = parseFloat(corners.borderTopRightRadius) || 0;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${left} 0 H${rect.width - right} Q${rect.width} 0 ${rect.width} ${right} V${rect.height - right} Q${rect.width} ${rect.height} ${rect.width - right} ${rect.height} H${left} Q0 ${rect.height} 0 ${rect.height - left} V${left} Q0 0 ${left} 0 Z`);
      perimeter = Math.max(path.getTotalLength(), 1);
      points = Array.from({ length: sampleCount }, (_, index) => {
        const point = path.getPointAtLength(index / sampleCount * perimeter);
        return { x: point.x, y: point.y };
      });
    };

    const pointAt = (distance: number) => {
      const position = ((distance % perimeter + perimeter) % perimeter) / perimeter * sampleCount;
      const index = Math.floor(position);
      const fraction = position - index;
      const first = points[index], second = points[(index + 1) % sampleCount];
      return { x: first.x + (second.x - first.x) * fraction, y: first.y + (second.y - first.y) * fraction };
    };

    const draw = (timestamp: number) => {
      context.clearRect(-padding, -padding, width, height);
      const sidebar = element.parentElement!;
      const visible = !mobile.matches || sidebar.classList.contains('mobile-open');
      if (visible && points.length) {
        startedAt ??= timestamp;
        const distance = ((timestamp - startedAt) % 16000) / 16000 * perimeter;
        const head = pointAt(distance);
        const tailLength = Math.min(135, perimeter * .07);
        const tail = pointAt(distance - tailLength);
        const gradient = context.createLinearGradient(tail.x, tail.y, head.x, head.y);
        gradient.addColorStop(0, 'rgba(76, 145, 239, 0)');
        gradient.addColorStop(.45, 'rgba(76, 145, 239, .35)');
        gradient.addColorStop(1, '#579aef');
        context.beginPath();
        for (let index = 0; index <= 48; index++) {
          const point = pointAt(distance - tailLength + index / 48 * tailLength);
          if (!index) context.moveTo(point.x, point.y);
          else context.lineTo(point.x, point.y);
        }
        context.strokeStyle = gradient;
        context.lineWidth = 2;
        context.lineCap = 'round';
        context.stroke();
        context.shadowColor = '#4c91ef';
        context.shadowBlur = 10;
        context.beginPath();
        context.arc(head.x, head.y, 3.5, 0, Math.PI * 2);
        context.fillStyle = '#e4f3ff';
        context.fill();
        context.shadowBlur = 0;
        context.strokeStyle = '#579aef';
        context.lineWidth = 1;
        context.stroke();
      }
      frameId = requestAnimationFrame(draw);
    };

    const syncMotion = () => {
      cancelAnimationFrame(frameId);
      context.clearRect(-padding, -padding, width, height);
      if (!motion.matches) frameId = requestAnimationFrame(draw);
    };
    resize();
    // Re-measuring the path costs ~40ms, far over a frame. While the sidebar's width animates, fade the light out
    // and re-measure once the size has settled, instead of on every frame of the animation.
    let settleTimer = 0, first = true;
    const observer = new ResizeObserver(() => {
      if (first) { first = false; return; }
      element.style.opacity = '0';
      clearTimeout(settleTimer);
      settleTimer = window.setTimeout(() => { resize(); element.style.opacity = ''; }, 160);
    });
    observer.observe(element);
    motion.addEventListener('change', syncMotion);
    syncMotion();
    return () => {
      observer.disconnect();
      clearTimeout(settleTimer);
      motion.removeEventListener('change', syncMotion);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return <div ref={ref} className="sidebar-orbit" aria-hidden="true"><canvas ref={canvasRef} /></div>;
}
