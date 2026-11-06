import {
  BAKE_DEPTH,
  BAKE_DETAIL,
  BAKE_EXTRA,
  BAKE_FIELDS,
  BAKE_STONE,
  COMPOSITE,
  VERTEX,
} from "./shaders";

/**
 * WebGL plumbing for the live marble. See shaders.ts for what is drawn; this
 * file only decides sizes, schedules the bake, and runs the composite.
 *
 * The bake is heavy (the stone and the vein distance fields take hundreds of
 * noise lookups per pixel), so it runs in horizontal strips, a few hundred
 * thousand pixels per frame, rather than as one long draw that could stall the
 * page or trip a GPU watchdog. A resize bakes into fresh textures while the
 * previous frame stays on screen, and swaps only when the new set is complete.
 */

/** CSS px → design px (the offline stone's grid; see shaders.ts). */
const DP_PER_CSS = 1.915;
/** Width of the offline stone in design px; the stone is anchored to its right edge. */
const STONE_W_DP = 1800;
/** The low-frequency fields are baked at this fraction of full resolution. */
const LOW_RES = 4;
/** Ceiling on the backing store, so a big retina window stays affordable. */
export const MAX_PIXELS = 3.6e6;
/** Bake budget per frame, per full-res pass. */
const STRIP_PIXELS = 300_000;
/** The vein picker in the composite repeats every 97 cycles; the clock wraps with it. */
const PICK_PERIOD = 97;

export function renderScale(cssW: number, cssH: number, dpr: number): number {
  let r = Math.min(Math.max(dpr, 1), 2);
  const area = cssW * cssH;
  if (area > 0 && area * r * r > MAX_PIXELS) r = Math.sqrt(MAX_PIXELS / area);
  return r;
}

/** Cycles elapsed on a clock of `period` seconds, wrapped where the shader repeats. */
export function cycleClock(t: number, period: number): number {
  return (t / period) % PICK_PERIOD;
}

export interface MarbleRenderer {
  /** Start baking for a new size. The current frame stays up until it is done. */
  resize(cssW: number, cssH: number, dpr: number): void;
  /** True while a bake is in progress (the loop should keep ticking). */
  baking(): boolean;
  /**
   * Advance one frame: bake the next strip, or composite the veins at time
   * `t` seconds. Returns true when the canvas was drawn this frame.
   */
  frame(t: number): boolean;
  dispose(): void;
}

type GL = WebGLRenderingContext;

interface Target {
  tex: WebGLTexture;
  fbo: WebGLFramebuffer;
  w: number;
  h: number;
}

interface Program {
  prog: WebGLProgram;
  loc(name: string): WebGLUniformLocation | null;
}

interface TextureSet {
  cssW: number;
  cssH: number;
  stone: Target;
  detail: Target;
  fields: Target;
  depth: Target;
  extra: Target;
}

interface Bake {
  set: TextureSet;
  row: number;
}

/* Vein clocks, in seconds per cycle. Different and coprime, so the three
   sets never fall into step; the whole picture only repeats after hours. */
const PERIOD_1 = 16;
const PERIOD_2 = 21;
const PERIOD_3 = 13;
/* The resting depths drift between two versions over this period. */
const DEPTH_DRIFT = 53;

function compile(gl: GL, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS) && !gl.isContextLost()) {
    console.warn("[marble] shader failed to compile:", gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function link(gl: GL, vs: WebGLShader, fsSource: string): Program | null {
  const fs = compile(gl, gl.FRAGMENT_SHADER, fsSource);
  const prog = gl.createProgram();
  if (!fs || !prog) return null;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.bindAttribLocation(prog, 0, "aPos");
  gl.linkProgram(prog);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS) && !gl.isContextLost()) {
    console.warn("[marble] program failed to link:", gl.getProgramInfoLog(prog));
    gl.deleteProgram(prog);
    return null;
  }
  const cache = new Map<string, WebGLUniformLocation | null>();
  return {
    prog,
    loc(name) {
      if (!cache.has(name)) cache.set(name, gl.getUniformLocation(prog, name));
      return cache.get(name) ?? null;
    },
  };
}

function makeTarget(gl: GL, w: number, h: number, filter: number): Target | null {
  const tex = gl.createTexture();
  const fbo = gl.createFramebuffer();
  if (!tex || !fbo) return null;
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (!ok) {
    gl.deleteFramebuffer(fbo);
    gl.deleteTexture(tex);
    return null;
  }
  return { tex, fbo, w, h };
}

function freeTarget(gl: GL, t: Target) {
  gl.deleteFramebuffer(t.fbo);
  gl.deleteTexture(t.tex);
}

export function createMarbleRenderer(canvas: HTMLCanvasElement): MarbleRenderer | null {
  const attrs: WebGLContextAttributes = {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
    powerPreference: "low-power",
  };
  const ctx = (canvas.getContext("webgl2", attrs) ??
    canvas.getContext("webgl", attrs)) as GL | null;
  if (!ctx) return null;
  const gl: GL = ctx;

  // The noise needs full float precision; without it the veins band and crawl.
  const high = gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER, gl.HIGH_FLOAT);
  if (!high || high.precision < 23) return null;

  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX);
  if (!vs) return null;
  const programs = [BAKE_STONE, BAKE_DETAIL, BAKE_FIELDS, BAKE_DEPTH, BAKE_EXTRA, COMPOSITE].map(
    (src) => link(gl, vs, src),
  );
  gl.deleteShader(vs);
  if (programs.some((p) => !p)) {
    programs.forEach((p) => p && gl.deleteProgram(p.prog));
    return null;
  }
  const [pStone, pDetail, pFields, pDepth, pExtra, pComposite] = programs as Program[];

  // One oversized triangle covers the whole target.
  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.disable(gl.DEPTH_TEST);
  gl.disable(gl.BLEND);

  let current: TextureSet | null = null;
  let bake: Bake | null = null;

  function allocate(cssW: number, cssH: number, dpr: number): TextureSet | null {
    const r = renderScale(cssW, cssH, dpr);
    const max = gl.getParameter(gl.MAX_TEXTURE_SIZE) as number;
    const w = Math.min(Math.max(1, Math.round(cssW * r)), max);
    const h = Math.min(Math.max(1, Math.round(cssH * r)), max);
    const lw = Math.max(1, Math.ceil(w / LOW_RES));
    const lh = Math.max(1, Math.ceil(h / LOW_RES));
    const stone = makeTarget(gl, w, h, gl.NEAREST);
    const detail = makeTarget(gl, w, h, gl.NEAREST);
    const fields = makeTarget(gl, lw, lh, gl.LINEAR);
    const depth = makeTarget(gl, lw, lh, gl.LINEAR);
    const extra = makeTarget(gl, lw, lh, gl.LINEAR);
    if (!stone || !detail || !fields || !depth || !extra) {
      [stone, detail, fields, depth, extra].forEach((t) => t && freeTarget(gl, t));
      return null;
    }
    return { cssW, cssH, stone, detail, fields, depth, extra };
  }

  function freeSet(set: TextureSet) {
    [set.stone, set.detail, set.fields, set.depth, set.extra].forEach((t) => freeTarget(gl, t));
  }

  /** Shared mapping uniforms: where this target's pixels sit in design space. */
  function applyMapping(p: Program, set: TextureSet, w: number, h: number) {
    gl.useProgram(p.prog);
    gl.uniform2f(p.loc("uRes"), w, h);
    gl.uniform2f(p.loc("uPxToDp"), (set.cssW * DP_PER_CSS) / w, (set.cssH * DP_PER_CSS) / h);
    gl.uniform1f(p.loc("uOriginX"), STONE_W_DP - set.cssW * DP_PER_CSS);
  }

  function bakePass(p: Program, set: TextureSet, t: Target, row0: number, rows: number) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fbo);
    gl.viewport(0, 0, t.w, t.h);
    applyMapping(p, set, t.w, t.h);
    gl.enable(gl.SCISSOR_TEST);
    gl.scissor(0, row0, t.w, rows);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.disable(gl.SCISSOR_TEST);
  }

  function bakeStep(job: Bake): boolean {
    const { set } = job;
    if (job.row === 0) {
      // The quarter-res passes are cheap; do them whole, up front.
      bakePass(pFields, set, set.fields, 0, set.fields.h);
      bakePass(pDepth, set, set.depth, 0, set.depth.h);
      bakePass(pExtra, set, set.extra, 0, set.extra.h);
    }
    const rows = Math.max(1, Math.floor(STRIP_PIXELS / set.stone.w));
    bakePass(pStone, set, set.stone, job.row, rows);
    bakePass(pDetail, set, set.detail, job.row, rows);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    job.row += rows;
    return job.row >= set.stone.h;
  }

  function composite(set: TextureSet, t: number) {
    const { w, h } = set.stone;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, w, h);
    applyMapping(pComposite, set, w, h);
    const units: Array<[string, Target]> = [
      ["uStone", set.stone],
      ["uDetail", set.detail],
      ["uFields", set.fields],
      ["uDepth", set.depth],
      ["uExtra", set.extra],
    ];
    units.forEach(([name, target], i) => {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, target.tex);
      gl.uniform1i(pComposite.loc(name), i);
    });
    gl.uniform1f(pComposite.loc("uCycles1"), cycleClock(t, PERIOD_1));
    gl.uniform1f(pComposite.loc("uCycles2"), cycleClock(t, PERIOD_2));
    gl.uniform1f(pComposite.loc("uCycles3"), cycleClock(t, PERIOD_3));
    gl.uniform1f(
      pComposite.loc("uDepthMix"),
      0.5 - 0.5 * Math.cos((2 * Math.PI * t) / DEPTH_DRIFT),
    );
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  return {
    resize(cssW, cssH, dpr) {
      if (gl.isContextLost() || cssW < 1 || cssH < 1) return;
      const r = renderScale(cssW, cssH, dpr);
      const target = bake?.set ?? current;
      if (
        target &&
        target.cssW === cssW &&
        target.cssH === cssH &&
        target.stone.w === Math.round(cssW * r)
      ) {
        return;
      }
      if (bake) freeSet(bake.set);
      const set = allocate(cssW, cssH, dpr);
      bake = set ? { set, row: 0 } : null;
    },
    baking() {
      return bake !== null;
    },
    frame(t) {
      if (gl.isContextLost()) return false;
      if (bake) {
        if (!bakeStep(bake)) return false;
        if (current) freeSet(current);
        current = bake.set;
        bake = null;
      }
      if (!current) return false;
      composite(current, t);
      return true;
    },
    dispose() {
      if (bake) freeSet(bake.set);
      if (current) freeSet(current);
      bake = null;
      current = null;
      programs.forEach((p) => p && gl.deleteProgram(p.prog));
      gl.deleteBuffer(quad);
    },
  };
}
