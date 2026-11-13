import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useFrameLoop, useImage, useStage } from "./stage";
import { useLowPower } from "./perf";

/* ────────────────────────────────────────────────────────────────
   A cut-out photograph that moves like a plant in a breeze.

   The image is drawn on a finely divided mesh and the vertex shader bends
   it about a pivot at its base: nothing moves at the pivot, the tips move
   most, and the top lags the bottom a little so the motion whips rather
   than rocks. Leaves get a smaller, faster flutter of their own. A rigid
   CSS rotation reads as the vase rocking; this reads as wind.

   No WebGL (or a lost context) falls back to the plain image with a gentle
   CSS sway; reduced motion draws one still frame.
   ──────────────────────────────────────────────────────────────── */

export interface SwayProps {
  src: string;
  /** Part of the image to draw: [x0, y0, x1, y1] in 0..1. */
  crop?: [number, number, number, number];
  /** Drawn size of the cropped image, stage px. */
  width: number;
  height: number;
  /** Room around the image so bent edges are not clipped, stage px. */
  pad?: number;
  /** Where the plant is anchored, in the cropped image's 0..1 space. */
  pivot?: [number, number];
  /** Bend at the tips, radians. */
  bend?: number;
  /** Leaf flutter at the tips, stage px. */
  flutter?: number;
  speed?: number;
  /** Fade the bottom of the crop out between these two y values (0..1). */
  fade?: [number, number];
  /** Narrow that fade to the middle, so the sides keep their edge. */
  fadeCenter?: number;
  seed?: number;
  /** Backing-store resolution as a fraction of on-screen pixels. Below 1 it
      renders soft — for out-of-focus foreground foliage that is the point,
      and it costs a fraction of the pixels. */
  resolution?: number;
  className?: string;
  style?: CSSProperties;
}

const VERT = `
attribute vec2 a_uv;
uniform vec2 u_size;      // drawn image size (px)
uniform vec2 u_canvas;    // canvas size (px)
uniform float u_pad;
uniform vec2 u_pivot;     // 0..1 in image space
uniform float u_time;
uniform float u_bend;
uniform float u_flutter;
uniform float u_seed;
varying vec2 v_uv;

float gust(float t) {
  return 0.55 * sin(t * 0.83 + u_seed)
       + 0.28 * sin(t * 1.71 + 1.3 + u_seed * 2.0)
       + 0.17 * sin(t * 2.93 + 0.4);
}

void main() {
  vec2 p = a_uv * u_size;
  vec2 piv = u_pivot * u_size;
  float above = max(piv.y - p.y, 0.0);
  float h = clamp(above / max(piv.y, 1.0), 0.0, 1.0);
  // the top lags the base: the gust reaches the tips a moment later
  float theta = u_bend * pow(h, 1.35) * gust(u_time - h * 0.55);
  vec2 d = p - piv;
  float c = cos(theta);
  float s = sin(theta);
  vec2 q = piv + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
  // leaf flutter, strongest at the ends and the outer edges
  float edge = 0.5 + abs(a_uv.x - u_pivot.x);
  q.x += u_flutter * h * edge * sin(u_time * 2.6 + a_uv.y * 11.0 + a_uv.x * 6.0 + u_seed);
  q.y += u_flutter * 0.55 * h * edge * sin(u_time * 3.4 + a_uv.x * 13.0 + u_seed * 1.7);
  vec2 pos = (q + vec2(u_pad)) / u_canvas;
  gl_Position = vec4(pos.x * 2.0 - 1.0, 1.0 - pos.y * 2.0, 0.0, 1.0);
  v_uv = a_uv;
}`;

const FRAG = `
precision mediump float;
uniform sampler2D u_tex;
uniform vec4 u_crop;
uniform vec2 u_fade;
uniform float u_fadeCenter;
varying vec2 v_uv;
void main() {
  vec2 uv = mix(u_crop.xy, u_crop.zw, v_uv);
  vec4 c = texture2D(u_tex, uv);
  float f = 1.0;
  if (u_fade.y > u_fade.x) {
    // the fade line dips lower towards the sides when fadeCenter > 0
    float lift = u_fadeCenter * pow(abs(v_uv.x - 0.5) * 2.0, 2.0);
    f = 1.0 - smoothstep(u_fade.x + lift, u_fade.y + lift, v_uv.y);
  }
  gl_FragColor = c * f;
}`;

const GRID = 44;

function compile(gl: WebGLRenderingContext, type: number, src: string) {
  const sh = gl.createShader(type);
  if (!sh) return null;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.warn(gl.getShaderInfoLog(sh));
    return null;
  }
  return sh;
}

interface Renderer {
  draw: (t: number) => void;
  resize: (w: number, h: number) => void;
  dispose: () => void;
}

function createRenderer(
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  p: Required<Omit<SwayProps, "className" | "style" | "resolution">>,
): Renderer | null {
  const gl = canvas.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: true });
  if (!gl) return null;
  const vs = compile(gl, gl.VERTEX_SHADER, VERT);
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) return null;
  const prog = gl.createProgram()!;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
  gl.useProgram(prog);

  // grid mesh
  const verts: number[] = [];
  for (let y = 0; y <= GRID; y++) for (let x = 0; x <= GRID; x++) verts.push(x / GRID, y / GRID);
  const idx: number[] = [];
  for (let y = 0; y < GRID; y++)
    for (let x = 0; x < GRID; x++) {
      const i = y * (GRID + 1) + x;
      idx.push(i, i + 1, i + GRID + 1, i + 1, i + GRID + 2, i + GRID + 1);
    }
  const vb = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vb);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
  const ib = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "a_uv");
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const u = (n: string) => gl.getUniformLocation(prog, n);
  const cw = p.width + p.pad * 2;
  const ch = p.height + p.pad * 2;
  gl.uniform2f(u("u_size"), p.width, p.height);
  gl.uniform2f(u("u_canvas"), cw, ch);
  gl.uniform1f(u("u_pad"), p.pad);
  gl.uniform2f(u("u_pivot"), p.pivot[0], p.pivot[1]);
  gl.uniform1f(u("u_bend"), p.bend);
  gl.uniform1f(u("u_flutter"), p.flutter);
  gl.uniform1f(u("u_seed"), p.seed);
  gl.uniform4f(u("u_crop"), p.crop[0], p.crop[1], p.crop[2], p.crop[3]);
  gl.uniform2f(u("u_fade"), p.fade[0], p.fade[1]);
  gl.uniform1f(u("u_fadeCenter"), p.fadeCenter);
  const uTime = u("u_time");

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.clearColor(0, 0, 0, 0);

  return {
    draw(t) {
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(uTime, t * p.speed);
      gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
    },
    resize(w, h) {
      canvas.width = w;
      canvas.height = h;
    },
    dispose() {
      gl.deleteBuffer(vb);
      gl.deleteBuffer(ib);
      gl.deleteTexture(tex);
      gl.deleteProgram(prog);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    },
  };
}

export function SwayImage({
  src,
  crop = [0, 0, 1, 1],
  width,
  height,
  pad = 40,
  pivot = [0.5, 1],
  bend = 0.05,
  flutter = 2,
  speed = 1,
  fade = [0, 0],
  fadeCenter = 0,
  seed = 0,
  resolution = 1,
  className,
  style,
}: SwayProps) {
  const { scale } = useStage();
  const img = useImage(src);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderer = useRef<Renderer | null>(null);
  const [failed, setFailed] = useState(false);
  /* A lost context cannot be revived on the same canvas, so recovery mounts
     a fresh one (a new key). Three goes, then the CSS fallback. */
  const [gen, setGen] = useState(0);
  const cw = width + pad * 2;
  const ch = height + pad * 2;

  // Built once per image and canvas; the props are fixed for a placement.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!img || !canvas || failed) return undefined;
    const retry = () => (gen < 3 ? setGen((g) => g + 1) : setFailed(true));
    const r = createRenderer(canvas, img, { src, crop, width, height, pad, pivot, bend, flutter, speed, fade, fadeCenter, seed });
    if (!r) {
      retry();
      return undefined;
    }
    renderer.current = r;
    const onLost = (e: Event) => {
      e.preventDefault();
      renderer.current = null;
      retry();
    };
    canvas.addEventListener("webglcontextlost", onLost);
    return () => {
      canvas.removeEventListener("webglcontextlost", onLost);
      r.dispose();
      renderer.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [img, failed, gen]);

  // Backing store follows the on-screen size (stage scale × device pixels).
  useEffect(() => {
    const r = renderer.current;
    if (!r) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2) * resolution;
    r.resize(Math.max(2, Math.round(cw * scale * dpr)), Math.max(2, Math.round(ch * scale * dpr)));
    r.draw(0);
  }, [scale, cw, ch, img, failed, gen, resolution]);

  const lowPower = useLowPower();
  useFrameLoop((t) => renderer.current?.draw(t + seed * 7), !!img && !failed && !lowPower, 30);

  const box: CSSProperties = { position: "absolute", width: cw, height: ch, ...style };

  // The file is missing: draw nothing rather than an empty canvas.
  if (img === false) return null;

  if (failed) {
    const [x0, y0, x1, y1] = crop;
    return (
      <div className={className} style={box}>
        <div
          className="v1-sway-fallback"
          style={{
            position: "absolute",
            left: pad,
            top: pad,
            width,
            height,
            backgroundImage: `url(${src})`,
            backgroundSize: `${(width / (x1 - x0)).toFixed(1)}px ${(height / (y1 - y0)).toFixed(1)}px`,
            backgroundPosition: `${(-x0 * width) / (x1 - x0)}px ${(-y0 * height) / (y1 - y0)}px`,
            transformOrigin: `${pivot[0] * 100}% ${pivot[1] * 100}%`,
          }}
        />
      </div>
    );
  }

  return <canvas key={gen} ref={canvasRef} className={className} style={box} aria-hidden />;
}
