/**
 * Professional dual-flow particle field for hourly submit vs fill notional.
 * X = time · Y = magnitude · amber = submit · cyan = fill · white sparks = conversion.
 */
import * as THREE from "three";

function makeGlowTexture() {
  const size = 128;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grd.addColorStop(0, "rgba(255,255,255,1)");
  grd.addColorStop(0.25, "rgba(255,255,255,0.55)");
  grd.addColorStop(0.55, "rgba(255,255,255,0.12)");
  grd.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

export class VolumeLandscape3D {
  constructor(canvas) {
    this.canvas = canvas;
    this._sig = "";
    this._raf = 0;
    this._t = 0;
    this._drag = { active: false, lx: 0, ly: 0, rotY: 0.55, rotX: 0.48 };
    this._layers = { submit: null, fill: null, convert: null, dust: null };
    this._meta = { maxY: 8, span: 20 };
    this.glow = makeGlowTexture();

    this._init();
    this._bind();
    this._loop();
  }

  _init() {
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x030305, 0.018);

    const w = this.canvas.clientWidth || 1400;
    const h = this.canvas.clientHeight || 700;
    this.camera = new THREE.PerspectiveCamera(36, w / h, 0.1, 300);
    this.camera.position.set(0, 11, 28);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h, false);
    this.renderer.setClearColor(0x030305, 1);

    this.scene.add(new THREE.AmbientLight(0x303040, 0.8));

    // Soft floor disc
    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(32, 64),
      new THREE.MeshBasicMaterial({
        color: 0x0a0a12,
        transparent: true,
        opacity: 0.9,
      })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.02;
    this.scene.add(floor);

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(18, 18.15, 96),
      new THREE.MeshBasicMaterial({
        color: 0xe89a3c,
        transparent: true,
        opacity: 0.18,
        side: THREE.DoubleSide,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.01;
    this.scene.add(ring);

    // Subtle radial tick marks
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const tick = new THREE.Mesh(
        new THREE.PlaneGeometry(0.08, 1.2),
        new THREE.MeshBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.06,
          side: THREE.DoubleSide,
        })
      );
      tick.position.set(Math.cos(a) * 17.5, 0.02, Math.sin(a) * 17.5);
      tick.rotation.x = -Math.PI / 2;
      tick.rotation.z = a;
      this.scene.add(tick);
    }

    this.root = new THREE.Group();
    this.scene.add(this.root);

    this._buildDust(1800);
  }

  _bind() {
    window.addEventListener("resize", () => {
      const w = this.canvas.clientWidth;
      const h = this.canvas.clientHeight;
      if (!w || !h) return;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    });

    this.canvas.addEventListener("pointerdown", (e) => {
      this._drag.active = true;
      this._drag.lx = e.clientX;
      this._drag.ly = e.clientY;
      this.canvas.setPointerCapture?.(e.pointerId);
    });
    window.addEventListener("pointerup", () => { this._drag.active = false; });
    window.addEventListener("pointermove", (e) => {
      if (!this._drag.active) return;
      this._drag.rotY += (e.clientX - this._drag.lx) * 0.0045;
      this._drag.rotX += (e.clientY - this._drag.ly) * 0.0035;
      this._drag.rotX = Math.max(0.22, Math.min(1.05, this._drag.rotX));
      this._drag.lx = e.clientX;
      this._drag.ly = e.clientY;
    });
  }

  update(hours, submitWan, fillWan) {
    const hoursSafe = hours || [];
    const sub = submitWan || [];
    const fill = fillWan || [];
    const sig = JSON.stringify([hoursSafe, sub, fill]);
    if (sig === this._sig) return;
    this._sig = sig;
    this._rebuild(hoursSafe, sub, fill);
  }

  _disposeLayer(key) {
    const layer = this._layers[key];
    if (!layer) return;
    this.root.remove(layer.points);
    layer.points.geometry.dispose();
    layer.points.material.dispose();
    this._layers[key] = null;
  }

  _buildDust(count) {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 8 + Math.random() * 22;
      const a = Math.random() * Math.PI * 2;
      pos[i * 3] = Math.cos(a) * r;
      pos[i * 3 + 1] = Math.random() * 14;
      pos[i * 3 + 2] = Math.sin(a) * r;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(
      geo,
      new THREE.PointsMaterial({
        map: this.glow,
        color: 0x8899aa,
        size: 0.18,
        transparent: true,
        opacity: 0.22,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        sizeAttenuation: true,
      })
    );
    this.scene.add(pts);
    this._layers.dust = { points: pts, count };
  }

  _rebuild(hours, submit, fills) {
    this._disposeLayer("submit");
    this._disposeLayer("fill");
    this._disposeLayer("convert");
    // clear hour markers
    while (this.root.children.length) {
      const o = this.root.children[0];
      this.root.remove(o);
      if (o.geometry) o.geometry.dispose();
      if (o.material) o.material.dispose();
    }

    const n = hours.length;
    if (!n) return;

    const maxV = Math.max(...submit, ...fills, 1);
    const span = Math.min(26, Math.max(14, n * 1.7));
    const gap = span / Math.max(n - 1, 1);
    const startX = -span / 2;
    const maxY = 9.5;
    this._meta = { maxY, span, gap, startX, n, maxV };

    // Hour baseline ticks
    for (let i = 0; i < n; i++) {
      const x = startX + i * gap;
      const line = new THREE.Mesh(
        new THREE.BoxGeometry(0.04, 0.02, 3.2),
        new THREE.MeshBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.08,
        })
      );
      line.position.set(x, 0.01, 0);
      this.root.add(line);
    }

    this._layers.submit = this._makeColumnField({
      values: submit,
      maxV,
      startX,
      gap,
      maxY,
      z: 0.85,
      color: 0xe89a3c,
      size: 0.42,
      density: 1.0,
      width: 0.55,
    });

    this._layers.fill = this._makeColumnField({
      values: fills,
      maxV,
      startX,
      gap,
      maxY,
      z: -0.85,
      color: 0x3ecfff,
      size: 0.38,
      density: 1.15,
      width: 0.5,
    });

    this._layers.convert = this._makeConversionField({
      submit,
      fills,
      maxV,
      startX,
      gap,
      maxY,
    });

    this.root.add(this._layers.submit.points);
    this.root.add(this._layers.fill.points);
    this.root.add(this._layers.convert.points);
  }

  /**
   * Gaussian vertical columns — height & particle count ∝ hourly notional.
   */
  _makeColumnField({ values, maxV, startX, gap, maxY, z, color, size, density, width }) {
    const n = values.length;
    let total = 0;
    const counts = values.map((v) => {
      const c = Math.max(24, Math.round((v / maxV) * 420 * density + 40));
      total += c;
      return c;
    });

    const pos = new Float32Array(total * 3);
    const phase = new Float32Array(total);
    const speed = new Float32Array(total);
    const home = new Float32Array(total * 3);

    let idx = 0;
    for (let i = 0; i < n; i++) {
      const x0 = startX + i * gap;
      const h = Math.max(0.35, (values[i] / maxV) * maxY);
      const c = counts[i];
      for (let k = 0; k < c; k++) {
        // denser near core, taller spread for larger volume
        const u = Math.random();
        const y = Math.pow(u, 0.55) * h;
        const spread = width * (0.35 + (1 - y / h) * 0.85);
        const ang = Math.random() * Math.PI * 2;
        const rr = Math.sqrt(Math.random()) * spread;
        const x = x0 + Math.cos(ang) * rr;
        const zz = z + Math.sin(ang) * rr * 0.7;

        pos[idx * 3] = x;
        pos[idx * 3 + 1] = y;
        pos[idx * 3 + 2] = zz;
        home[idx * 3] = x0;
        home[idx * 3 + 1] = h;
        home[idx * 3 + 2] = z;
        phase[idx] = Math.random() * Math.PI * 2;
        speed[idx] = 0.35 + Math.random() * 0.9;
        idx++;
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      map: this.glow,
      color,
      size,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const points = new THREE.Points(geo, mat);
    return { points, pos, phase, speed, home, count: total, kind: "column" };
  }

  /**
   * Conversion sparks arc from submit peak → fill peak (visual fill-rate flow).
   */
  _makeConversionField({ submit, fills, maxV, startX, gap, maxY }) {
    const n = submit.length;
    const perArc = 28;
    const total = n * perArc;
    const pos = new Float32Array(total * 3);
    const phase = new Float32Array(total);
    const speed = new Float32Array(total);
    const curves = [];

    for (let i = 0; i < n; i++) {
      const x = startX + i * gap;
      const h0 = Math.max(0.4, (submit[i] / maxV) * maxY);
      const h1 = Math.max(0.35, (fills[i] / maxV) * maxY);
      const rate = submit[i] > 0 ? Math.min(1, fills[i] / submit[i]) : 0;
      const midY = Math.max(h0, h1) + 1.2 + rate * 2.2;
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(x, h0 * 0.92, 0.85),
        new THREE.Vector3(x + 0.15, midY, 0),
        new THREE.Vector3(x, h1 * 0.92, -0.85)
      );
      curves.push({ curve, rate });
      for (let k = 0; k < perArc; k++) {
        const id = i * perArc + k;
        phase[id] = k / perArc + Math.random() * 0.05;
        speed[id] = 0.12 + rate * 0.28 + Math.random() * 0.08;
        const pt = curve.getPoint(phase[id] % 1);
        pos[id * 3] = pt.x;
        pos[id * 3 + 1] = pt.y;
        pos[id * 3 + 2] = pt.z;
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      map: this.glow,
      color: 0xffffff,
      size: 0.22,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const points = new THREE.Points(geo, mat);
    return { points, pos, phase, speed, curves, perArc, count: total, kind: "convert" };
  }

  _animate(dt) {
    // Column shimmer + slow rise recycle
    for (const key of ["submit", "fill"]) {
      const L = this._layers[key];
      if (!L) continue;
      const arr = L.pos;
      for (let i = 0; i < L.count; i++) {
        const h = L.home[i * 3 + 1];
        const x0 = L.home[i * 3];
        const z0 = L.home[i * 3 + 2];
        arr[i * 3 + 1] += L.speed[i] * dt * 0.55;
        const wobble = Math.sin(this._t * L.speed[i] + L.phase[i]) * 0.04;
        arr[i * 3] = x0 + (arr[i * 3] - x0) * 0.98 + wobble;
        arr[i * 3 + 2] = z0 + (arr[i * 3 + 2] - z0) * 0.98;
        if (arr[i * 3 + 1] > h + 0.6) {
          arr[i * 3 + 1] = Math.random() * 0.2;
          const ang = Math.random() * Math.PI * 2;
          const rr = Math.random() * 0.45;
          arr[i * 3] = x0 + Math.cos(ang) * rr;
          arr[i * 3 + 2] = z0 + Math.sin(ang) * rr * 0.7;
        }
      }
      L.points.geometry.attributes.position.needsUpdate = true;
      L.points.material.opacity = 0.72 + Math.sin(this._t * 1.2) * 0.08;
    }

    // Conversion flow along arcs
    const C = this._layers.convert;
    if (C) {
      for (let i = 0; i < C.count; i++) {
        const arc = Math.floor(i / C.perArc);
        const curve = C.curves[arc]?.curve;
        if (!curve) continue;
        C.phase[i] = (C.phase[i] + dt * C.speed[i]) % 1;
        const pt = curve.getPoint(C.phase[i]);
        C.pos[i * 3] = pt.x;
        C.pos[i * 3 + 1] = pt.y;
        C.pos[i * 3 + 2] = pt.z;
      }
      C.points.geometry.attributes.position.needsUpdate = true;
    }

    // Ambient dust drift
    const D = this._layers.dust;
    if (D) {
      const arr = D.points.geometry.attributes.position.array;
      for (let i = 0; i < D.count; i++) {
        arr[i * 3 + 1] += Math.sin(this._t * 0.4 + i) * 0.002;
        arr[i * 3] += Math.cos(this._t * 0.15 + i * 0.01) * 0.0015;
      }
      D.points.geometry.attributes.position.needsUpdate = true;
    }
  }

  _loop() {
    const tick = () => {
      this._raf = requestAnimationFrame(tick);
      const dt = 0.016;
      this._t += dt;

      if (!this._drag.active) this._drag.rotY += dt * 0.06;

      const r = 27;
      const ry = this._drag.rotY;
      const rx = this._drag.rotX;
      this.camera.position.x = Math.sin(ry) * Math.cos(rx) * r;
      this.camera.position.y = 4 + Math.sin(rx) * 16;
      this.camera.position.z = Math.cos(ry) * Math.cos(rx) * r;
      this.camera.lookAt(0, 3.2, 0);

      this.root.rotation.y = Math.sin(this._t * 0.12) * 0.025;
      this._animate(dt);
      this.renderer.render(this.scene, this.camera);
    };
    this._raf = requestAnimationFrame(tick);
  }

  dispose() {
    cancelAnimationFrame(this._raf);
    this.renderer.dispose();
    this.glow.dispose();
  }
}
