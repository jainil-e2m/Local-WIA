/**
 * Plays a "stacked alpha" video as a transparent layer.
 *
 * Each frame of the file carries the colour in its top half and the alpha
 * matte, as greyscale, in its bottom half. A tiny WebGL shader recombines
 * the two into premultiplied RGBA on a transparent canvas.
 *
 * WHY NOT A VIDEO WITH A REAL ALPHA CHANNEL. Browsers disagree about which
 * format carries alpha: Chrome and Firefox read it from WebM (VP9), Safari
 * only from HEVC — and each renders the other's file opaque, on a black box.
 * Choosing between two files per browser is fragile. An ordinary H.264 MP4
 * plays everywhere, and the matte rides along as plain pixels.
 *
 * The asset is built by scripts/build-hero-bouquet.py.
 */

const VERTEX = /* glsl */ `
attribute vec2 aPos;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`;

const FRAGMENT = /* glsl */ `
precision mediump float;
uniform sampler2D uVideo;
uniform vec2 uRes;
uniform float uHalfTexel; // keeps each half's samples off the other half

void main() {
  vec2 p = gl_FragCoord.xy / uRes;  // origin bottom-left
  float v = 1.0 - p.y;              // video rows run top-down
  float vc = clamp(v * 0.5, uHalfTexel, 0.5 - uHalfTexel);
  float va = clamp(0.5 + v * 0.5, 0.5 + uHalfTexel, 1.0 - uHalfTexel);
  vec3 rgb = texture2D(uVideo, vec2(p.x, vc)).rgb;
  float a = texture2D(uVideo, vec2(p.x, va)).r;
  // The codec leaves faint noise around 0 and 1; without this the whole
  // frame would carry a barely-visible veil, which is the box we are hiding.
  a = clamp((a - 0.03) / 0.94, 0.0, 1.0);
  gl_FragColor = vec4(rgb * a, a);
}
`;

export interface StackedAlphaPlayer {
  /** Match the backing store to the element's CSS size. */
  resize(cssW: number, cssH: number, dpr: number): void;
  /** Upload the video's current frame and draw it. */
  draw(video: HTMLVideoElement): void;
  dispose(): void;
}

function compile(gl: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, src);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS) && !gl.isContextLost()) {
    console.warn("[bouquet] shader failed to compile:", gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

export function createStackedAlphaPlayer(canvas: HTMLCanvasElement): StackedAlphaPlayer | null {
  const attrs: WebGLContextAttributes = {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: "low-power",
  };
  const ctx = (canvas.getContext("webgl2", attrs) ??
    canvas.getContext("webgl", attrs)) as WebGLRenderingContext | null;
  if (!ctx) return null;
  const gl: WebGLRenderingContext = ctx;

  const vs = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  const prog = gl.createProgram();
  if (!vs || !fs || !prog) return null;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.bindAttribLocation(prog, 0, "aPos");
  gl.linkProgram(prog);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS) && !gl.isContextLost()) {
    console.warn("[bouquet] program failed to link:", gl.getProgramInfoLog(prog));
    return null;
  }
  gl.useProgram(prog);
  const uRes = gl.getUniformLocation(prog, "uRes");
  const uHalfTexel = gl.getUniformLocation(prog, "uHalfTexel");
  gl.uniform1i(gl.getUniformLocation(prog, "uVideo"), 0);

  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  return {
    resize(cssW, cssH, dpr) {
      const r = Math.min(Math.max(dpr, 1), 2);
      const w = Math.max(1, Math.round(cssW * r));
      const h = Math.max(1, Math.round(cssH * r));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
    },
    draw(video) {
      if (gl.isContextLost() || video.readyState < 2 || !video.videoHeight) return;
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uHalfTexel, 0.5 / video.videoHeight);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
    dispose() {
      gl.deleteTexture(tex);
      gl.deleteBuffer(quad);
      gl.deleteProgram(prog);
    },
  };
}
