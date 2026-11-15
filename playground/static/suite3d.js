/* suite3d.js: low-poly three.js visuals for the venture suite. Plain script, no build step.
 *
 * window.Suite3D
 *   ok()                         -> true when THREE is loaded and WebGL works
 *   thumb(kind, {size})          -> PNG data URL (or null). One shared offscreen renderer, cached per kind+size.
 *                                   kinds: warehouse | flex | office | retail | mixed | apartments | unknown,
 *                                   'prop:<business group>', 'agent:<agent name>'
 *   map(el, {pins, onPick})      -> {setPins, select, dispose} or null. Dark low-poly Houston with pins.
 *   space(el, {sf, ceiling_ft, business, label}) -> {dispose, info} or null. The listed space, to scale,
 *                                   with the business drawn inside. info: {width_ft, depth_ft, height_ft,
 *                                   height_known, courts, assumed}
 * Every call returns null instead of throwing, so callers can fall back to 2D.
 */
(function () {
  'use strict';

  var C = {
    page: 0x07111F, panel: 0x0D1B2E, blue: 0x0054A6, med: 0x00B0E6, light: 0x9DDCF9, cyan: 0xE4F6FF,
    gold: 0xFFC20E, gray: 0x5A5A5A, wall: 0x1b3a5e, wall2: 0x24507d, roof: 0x2d5f92, dark: 0x0a1628,
    plate: 0x0f2036, floor: 0x0f2238
  };
  var PI = Math.PI;
  var BG = 0x0B0C0E;   // page background (neutral graphite)

  // Everything is drawn in neutral greys: any palette color maps to a grey of the same lightness.
  function grey(c) {
    var col = c instanceof THREE.Color ? c.clone() : new THREE.Color(c);
    var L = 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b;
    var g = Math.min(0.92, 0.09 + 0.8 * L);
    return new THREE.Color(g, g, g);
  }

  function PR() { return Math.min(window.devicePixelRatio || 1, 2); }
  function hasThree() { return typeof window.THREE !== 'undefined' && window.THREE && window.THREE.WebGLRenderer; }
  function warn(e) { try { if (window.console) console.warn('Suite3D:', e); } catch (_) { /* ignore */ } }
  function safe(fn, fallback) {
    return function () {
      try { return fn.apply(null, arguments); } catch (e) { warn(e); return fallback === undefined ? null : fallback; }
    };
  }

  var okCache = null;
  function ok() {
    if (okCache !== null) return okCache;
    if (!hasThree()) return false;            // THREE may still be loading; do not cache a miss
    try {
      var c = document.createElement('canvas');
      var gl = c.getContext('webgl2') || c.getContext('webgl') || c.getContext('experimental-webgl');
      okCache = !!gl;
      if (gl && gl.getExtension) {
        var lose = gl.getExtension('WEBGL_lose_context');
        if (lose) lose.loseContext();
      }
    } catch (e) { okCache = false; }
    return okCache;
  }

  // Seeded random so the map looks the same every load.
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------- materials and primitives ----------
  function mat(color, o) {
    o = o || {};
    var m = new THREE.MeshPhongMaterial({
      color: grey(color), flatShading: true, shininess: Math.min(o.shine == null ? 12 : o.shine, 20), specular: 0x161616
    });
    if (o.opacity != null && o.opacity < 1) {
      m.transparent = true; m.opacity = o.opacity; m.depthWrite = false;
    }
    if (o.side) m.side = o.side;
    return m;
  }
  function basic(color, opacity, additive) {
    var m = new THREE.MeshBasicMaterial({ color: grey(color) });
    if (opacity != null && opacity < 1) { m.transparent = true; m.opacity = opacity; }
    if (additive) { m.transparent = true; m.depthWrite = false; }   // no additive blending: nothing glows
    return m;
  }
  function edges(mesh, opacity, color) {
    var e = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 25),
      new THREE.LineBasicMaterial({ color: grey(color || C.med), transparent: true, opacity: opacity == null ? 0.35 : opacity }));
    mesh.add(e);
    return mesh;
  }
  // Box with its base at y.
  function box(parent, w, h, d, color, x, y, z, o) {
    o = o || {};
    var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), o.material || mat(color, o));
    m.position.set(x || 0, (y || 0) + h / 2, z || 0);
    if (o.ry) m.rotation.y = o.ry;
    if (o.rz) m.rotation.z = o.rz;
    if (o.edges !== false) edges(m, o.eo, o.ec);
    parent.add(m);
    return m;
  }
  // Any geometry centred at x,y,z.
  function put(parent, geo, color, x, y, z, o) {
    o = o || {};
    var m = new THREE.Mesh(geo, o.material || mat(color, o));
    m.position.set(x || 0, y || 0, z || 0);
    if (o.rx) m.rotation.x = o.rx;
    if (o.ry) m.rotation.y = o.ry;
    if (o.rz) m.rotation.z = o.rz;
    if (o.edges) edges(m, o.eo, o.ec);
    parent.add(m);
    return m;
  }
  function prism(parent, width, height, length, color, x, y, z, alongX) {
    var s = new THREE.Shape();
    s.moveTo(-width / 2, 0); s.lineTo(width / 2, 0); s.lineTo(0, height); s.lineTo(-width / 2, 0);
    var g = new THREE.ExtrudeGeometry(s, { depth: length, bevelEnabled: false });
    g.translate(0, 0, -length / 2);
    var m = put(parent, g, color, x, y, z, { ry: alongX ? PI / 2 : 0, edges: true, eo: 0.3 });
    return m;
  }
  function lights(scene) {
    scene.add(new THREE.HemisphereLight(0xffffff, 0x1a1a1a, 0.8));
    var d = new THREE.DirectionalLight(0xffffff, 0.7); d.position.set(5, 10, 7); scene.add(d);
    var rim = new THREE.DirectionalLight(0xffffff, 0.2); rim.position.set(-6, 3, -5); scene.add(rim);
  }
  function disposeTree(root) {
    root.traverse(function (o) {
      if (o.geometry) o.geometry.dispose();
      if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) { m.dispose(); });
    });
  }
  function fitCamera(cam, obj, dir, margin) {
    var b = new THREE.Box3().setFromObject(obj);
    var s = b.getBoundingSphere(new THREE.Sphere());
    var dist = s.radius / Math.sin(cam.fov * PI / 360) * (margin || 1.1);
    cam.position.copy(s.center).add(dir.normalize().multiplyScalar(dist));
    cam.near = dist / 50; cam.far = dist * 4;
    cam.lookAt(s.center);
    cam.updateProjectionMatrix();
  }

  // ---------- building archetypes ----------
  function glassMat(ei) { return mat(C.light, { emissive: C.light, ei: ei == null ? 0.35 : ei, shine: 60 }); }

  function makeBuilding(kind) {
    var g = new THREE.Group(), i, f, c;
    switch (kind) {
      case 'warehouse':
        box(g, 6, 1.8, 4, C.wall, 0, 0, 0);
        box(g, 6.15, 0.1, 4.15, C.roof, 0, 1.8, 0, { edges: false });
        for (i = 0; i < 4; i++) {
          box(g, 0.8, 1.0, 0.06, C.dark, -2.1 + i * 1.4, 0, 2.02, { edges: false });
          box(g, 0.24, 0.08, 0.06, C.med, -2.1 + i * 1.4, 1.15, 2.04, { material: basic(C.med), edges: false });
        }
        box(g, 0.06, 0.2, 3.2, C.light, 3.02, 1.35, 0, { material: glassMat(0.3), edges: false });
        box(g, 0.6, 0.3, 0.5, 0x3d5a78, -1.6, 1.9, -0.6);
        box(g, 0.8, 0.3, 0.6, 0x3d5a78, 0.4, 1.9, -0.9);
        box(g, 0.5, 0.25, 0.5, 0x3d5a78, 1.9, 1.9, 0.6);
        break;
      case 'flex':
        box(g, 5, 1.5, 3.2, C.wall2, 0, 0, 0);
        box(g, 5.1, 0.1, 3.3, C.roof, 0, 1.5, 0, { edges: false });
        box(g, 2.2, 1.0, 0.06, C.light, -1.2, 0.15, 1.62, { material: glassMat(0.4), edges: false });
        box(g, 1.1, 0.08, 0.5, C.roof, -1.2, 1.2, 1.85);
        for (i = 0; i < 2; i++) box(g, 0.9, 1.05, 0.06, C.dark, 0.8 + i * 1.2, 0, 1.62, { edges: false });
        box(g, 0.6, 0.28, 0.5, 0x3d5a78, 1.2, 1.6, -0.6);
        break;
      case 'office':
        box(g, 3.4, 0.5, 3.4, C.wall, 0, 0, 0, { eo: 0.25 });
        for (i = 0; i < 9; i++) {
          box(g, 2.4, 0.32, 2.4, C.wall2, 0, 0.5 + i * 0.46, 0, { edges: false });
          box(g, 2.46, 0.14, 2.46, C.light, 0, 0.82 + i * 0.46, 0, { material: glassMat(0.25), edges: false });
        }
        var shell = new THREE.Mesh(new THREE.BoxGeometry(2.46, 9 * 0.46, 2.46), basic(0, 0, false));
        shell.material.visible = false;
        shell.position.set(0, 0.5 + 9 * 0.46 / 2, 0); edges(shell, 0.45); g.add(shell);
        box(g, 1.6, 0.4, 1.6, C.roof, 0, 0.5 + 9 * 0.46, 0);
        put(g, new THREE.CylinderGeometry(0.03, 0.03, 0.9, 5), C.gray, 0.4, 0.5 + 9 * 0.46 + 0.85, 0.3);
        break;
      case 'retail':
        box(g, 7.6, 0.04, 2.2, 0x13263f, 0, 0, 1.9, { edges: false });
        for (i = 0; i < 10; i++) box(g, 0.04, 0.02, 0.9, 0x6f8aa6, -3.4 + i * 0.75, 0.04, 2.3, { edges: false });
        box(g, 7.4, 1.15, 2.2, C.wall, 0, 0, -0.3);
        box(g, 7.5, 0.12, 2.3, C.roof, 0, 1.15, -0.3, { edges: false });
        box(g, 7.6, 0.1, 0.55, C.roof, 0, 0.9, 1.06);
        for (i = 0; i < 5; i++) {
          box(g, 1.2, 0.72, 0.05, C.light, -2.9 + i * 1.45, 0.1, 0.82, { material: glassMat(0.35), edges: false });
          box(g, 0.9, 0.16, 0.05, C.med, -2.9 + i * 1.45, 1.06, 0.84, { material: basic(C.med), edges: false });
        }
        break;
      case 'mixed':
        box(g, 4.4, 1.0, 3.2, C.wall, 0, 0, 0);
        box(g, 4.2, 0.65, 0.05, C.light, 0, 0.12, 1.62, { material: glassMat(0.45), edges: false });
        box(g, 3.8, 2.1, 2.6, C.wall2, 0, 1.0, -0.15);
        for (f = 0; f < 3; f++) for (c = 0; c < 5; c++) {
          box(g, 0.42, 0.36, 0.04, C.light, -1.5 + c * 0.75, 1.2 + f * 0.66, 1.16, { material: glassMat(0.3), edges: false });
          if ((c + f) % 2 === 0) box(g, 0.6, 0.06, 0.28, C.roof, -1.5 + c * 0.75, 1.15 + f * 0.66, 1.3, { edges: false });
        }
        box(g, 3.9, 0.1, 2.7, C.roof, 0, 3.1, -0.15, { edges: false });
        box(g, 0.7, 0.35, 0.6, 0x3d5a78, 1.0, 3.2, -0.6);
        break;
      case 'apartments':
        box(g, 4.2, 1.7, 1.5, C.wall2, -0.2, 0, -0.9);
        box(g, 1.5, 1.7, 2.6, C.wall2, 1.15, 0, 1.15);
        prism(g, 1.6, 0.6, 4.3, C.roof, -0.2, 1.7, -0.9, true);
        prism(g, 1.6, 0.6, 2.7, C.roof, 1.15, 1.7, 1.15, false);
        for (f = 0; f < 3; f++) {
          for (c = 0; c < 6; c++) box(g, 0.3, 0.26, 0.04, C.light, -2.0 + c * 0.62, 0.2 + f * 0.52, -0.13, { material: glassMat(0.3), edges: false });
          for (c = 0; c < 3; c++) box(g, 0.04, 0.26, 0.3, C.light, 0.38, 0.2 + f * 0.52, 0.5 + c * 0.7, { material: glassMat(0.3), edges: false });
        }
        break;
      default: // unknown
        box(g, 3, 2, 3, C.gray, 0, 0, 0, { opacity: 0.35, eo: 0.8, ec: 0x9aa5b1 });
        box(g, 0.25, 0.25, 0.25, C.gray, 0, 2.3, 0, { eo: 0.6, ec: 0x9aa5b1 });
    }
    var b = new THREE.Box3().setFromObject(g), size = b.getSize(new THREE.Vector3()), mid = b.getCenter(new THREE.Vector3());
    box(g, size.x + 0.8, 0.12, size.z + 0.8, C.plate, mid.x, -0.12, mid.z, { eo: 0.25 });
    return g;
  }

  // ---------- business-group props ----------
  function makeProp(group) {
    var g = new THREE.Group();
    switch (group) {
      case 'Sports & fitness':
        var bell = put(g, new THREE.IcosahedronGeometry(1, 1), C.blue, 0, 1, 0, { edges: true, eo: 0.3 });
        bell.scale.set(1, 0.9, 1);
        put(g, new THREE.TorusGeometry(0.55, 0.15, 6, 12, PI), C.blue, 0, 1.65, 0, { edges: true, eo: 0.3 });
        box(g, 1.2, 0.12, 1.2, C.dark, 0, 0, 0, { edges: false });
        put(g, new THREE.IcosahedronGeometry(0.32, 1), C.gold, 1.35, 0.32, 0.6, { shine: 30 });
        break;
      case 'Food & drink':
        put(g, new THREE.CylinderGeometry(0.8, 0.6, 1.5, 10), C.cyan, 0, 0.75, 0, { edges: true, eo: 0.25 });
        put(g, new THREE.CylinderGeometry(0.76, 0.68, 0.5, 10), C.blue, 0, 0.8, 0);
        put(g, new THREE.CylinderGeometry(0.86, 0.86, 0.14, 10), C.med, 0, 1.55, 0, { edges: true, eo: 0.3 });
        put(g, new THREE.CylinderGeometry(0.55, 0.8, 0.16, 10), C.med, 0, 1.7, 0);
        break;
      case 'Health':
        box(g, 1.9, 1.2, 0.75, C.blue, 0, 0, 0);
        put(g, new THREE.TorusGeometry(0.35, 0.08, 5, 10, PI), C.gray, 0, 1.2, 0);
        box(g, 0.7, 0.2, 0.06, C.cyan, 0, 0.5, 0.4, { material: basic(C.cyan), edges: false });
        box(g, 0.2, 0.7, 0.06, C.cyan, 0, 0.25, 0.4, { material: basic(C.cyan), edges: false });
        break;
      case 'Personal services':
        put(g, new THREE.CylinderGeometry(0.6, 0.7, 0.12, 10), C.gray, 0, 0.06, 0);
        put(g, new THREE.CylinderGeometry(0.1, 0.1, 0.6, 6), C.gray, 0, 0.4, 0);
        box(g, 1.1, 0.25, 1.0, C.blue, 0, 0.7, 0);
        box(g, 1.1, 1.2, 0.2, C.blue, 0, 0.95, -0.45);
        box(g, 0.6, 0.3, 0.15, C.med, 0, 2.15, -0.45);
        box(g, 0.14, 0.12, 0.9, C.gray, -0.6, 1.05, 0, { edges: false });
        box(g, 0.14, 0.12, 0.9, C.gray, 0.6, 1.05, 0, { edges: false });
        box(g, 0.8, 0.1, 0.4, C.gray, 0, 0.25, 0.6, { edges: false });
        break;
      case 'Children & education':
        box(g, 0.9, 0.9, 0.9, C.blue, -0.5, 0, 0, { ry: 0.2 });
        box(g, 0.9, 0.9, 0.9, C.med, 0.5, 0, 0.15, { ry: -0.3 });
        box(g, 0.8, 0.8, 0.8, C.light, 0, 0.9, 0.05, { ry: 0.6 });
        put(g, new THREE.ConeGeometry(0.5, 0.6, 4), C.gold, 0, 2.0, 0.05, { ry: PI / 4 + 0.6, edges: true, eo: 0.3 });
        break;
      case 'Retail':
        box(g, 1.4, 1.6, 0.6, C.med, 0, 0, 0);
        box(g, 1.44, 0.18, 0.64, C.blue, 0, 1.42, 0, { edges: false });
        put(g, new THREE.TorusGeometry(0.3, 0.05, 5, 10, PI), C.cyan, -0.3, 1.6, 0);
        put(g, new THREE.TorusGeometry(0.3, 0.05, 5, 10, PI), C.cyan, 0.3, 1.6, 0);
        break;
      case 'Auto & storage':
        box(g, 2.6, 0.55, 1.2, C.blue, 0, 0.25, 0);
        box(g, 1.4, 0.45, 1.05, C.light, -0.15, 0.8, 0, { material: glassMat(0.2) });
        [[-0.8, 0.62], [0.8, 0.62], [-0.8, -0.62], [0.8, -0.62]].forEach(function (p) {
          put(g, new THREE.CylinderGeometry(0.3, 0.3, 0.22, 8), C.dark, p[0], 0.3, p[1], { rx: PI / 2, edges: true, eo: 0.4 });
        });
        box(g, 0.06, 0.12, 0.25, C.cyan, 1.3, 0.55, 0.35, { material: basic(C.cyan), edges: false });
        box(g, 0.06, 0.12, 0.25, C.cyan, 1.3, 0.55, -0.35, { material: basic(C.cyan), edges: false });
        break;
      default:
        box(g, 1.6, 1.2, 1.2, C.wall2, 0, 0, 0);
        for (var i = 0; i < 4; i++) box(g, 0.42, 0.08, 0.5, i % 2 ? C.cyan : C.med, -0.6 + i * 0.4, 1.0, 0.75, { rz: 0, edges: false });
        box(g, 0.8, 0.6, 0.05, C.light, 0, 0.1, 0.62, { material: glassMat(0.4), edges: false });
    }
    return g;
  }

  // ---------- agent avatars ----------
  var AGENT_TINT = {
    planner: C.med, site: C.blue, building: 0x2d6fb0, residents: C.light, competitors: 0x3a86c8,
    momentum: C.med, lookalike: 0x7fc8ec, coordinator: C.blue, money: 0x1f6fb8, deal: 0x4aa3d8,
    records: 0x5d8fb8, permits: 0x2a5a8a, verdict: C.light
  };
  function makeAgent(name) {
    var g = new THREE.Group(), tint = AGENT_TINT[name] || C.med;
    put(g, new THREE.IcosahedronGeometry(1, 1), tint, 0, 0, 0, { shine: 40, edges: true, eo: 0.25, ec: C.cyan });
    var visor = put(g, new THREE.BoxGeometry(1.3, 0.48, 0.4), C.dark, 0, 0.08, 0.72, { shine: 80 });
    visor.material.emissive = new THREE.Color(0x000000);
    put(g, new THREE.SphereGeometry(0.11, 8, 6), 0, -0.28, 0.1, 0.95, { material: basic(C.cyan) });
    put(g, new THREE.SphereGeometry(0.11, 8, 6), 0, 0.28, 0.1, 0.95, { material: basic(C.cyan) });
    put(g, new THREE.CylinderGeometry(0.18, 0.18, 0.2, 8), C.gray, -1.0, 0, 0, { rz: PI / 2 });
    put(g, new THREE.CylinderGeometry(0.18, 0.18, 0.2, 8), C.gray, 1.0, 0, 0, { rz: PI / 2 });
    switch (name) {
      case 'planner':
        put(g, new THREE.CylinderGeometry(0.04, 0.04, 0.55, 5), C.gray, 0, 1.2, 0);
        put(g, new THREE.IcosahedronGeometry(0.14, 0), 0, 0, 1.55, 0, { material: basic(C.med) });
        break;
      case 'site':
        put(g, new THREE.ConeGeometry(0.2, 0.42, 8), C.gold, 0, 1.3, 0, { rx: PI });
        put(g, new THREE.SphereGeometry(0.24, 8, 6), C.gold, 0, 1.55, 0);
        break;
      case 'building':
        put(g, new THREE.SphereGeometry(0.72, 10, 4, 0, 2 * PI, 0, PI / 2), C.gold, 0, 0.62, 0);
        put(g, new THREE.CylinderGeometry(0.9, 0.9, 0.06, 12), C.gold, 0, 0.64, 0.1);
        break;
      case 'residents':
        box(g, 0.5, 0.42, 0.5, C.cyan, 0, 0.92, 0);
        put(g, new THREE.ConeGeometry(0.45, 0.35, 4), C.blue, 0, 1.52, 0, { ry: PI / 4 });
        break;
      case 'competitors':
        put(g, new THREE.CylinderGeometry(0.03, 0.03, 0.85, 5), C.gray, 0.3, 1.3, 0);
        box(g, 0.42, 0.26, 0.03, C.med, 0.52, 1.45, 0, { material: basic(C.med), edges: false });
        break;
      case 'momentum':
        put(g, new THREE.CylinderGeometry(0.08, 0.08, 0.4, 6), C.med, 0, 1.15, 0);
        put(g, new THREE.ConeGeometry(0.22, 0.32, 6), 0, 0, 1.5, 0, { material: basic(C.med) });
        break;
      case 'lookalike':
        put(g, new THREE.TorusGeometry(0.55, 0.05, 6, 20), 0, 0, 1.25, 0, { rx: PI / 2, material: basic(C.light) });
        put(g, new THREE.TorusGeometry(0.38, 0.04, 6, 20), 0, 0, 1.4, 0, { rx: PI / 2, material: basic(C.med) });
        break;
      case 'coordinator':
        [C.med, C.light, C.cyan].forEach(function (col, k) {
          var a = k * 2 * PI / 3;
          put(g, new THREE.IcosahedronGeometry(0.14, 0), 0, Math.cos(a) * 0.6, 1.25, Math.sin(a) * 0.6, { material: basic(col) });
        });
        put(g, new THREE.TorusGeometry(0.6, 0.02, 4, 24), 0, 0, 1.25, 0, { rx: PI / 2, material: basic(C.med, 0.6) });
        break;
      case 'money':
        put(g, new THREE.CylinderGeometry(0.36, 0.36, 0.09, 14), C.gold, 0, 1.42, 0, { rx: PI / 2, edges: true, eo: 0.4, ec: C.cyan });
        break;
      case 'deal':
        box(g, 0.55, 0.34, 0.06, C.light, 0, 1.2, 0, { rz: 0.3 });
        put(g, new THREE.SphereGeometry(0.05, 6, 4), C.dark, -0.18, 1.32, 0.05);
        break;
      case 'records':
        put(g, new THREE.TorusGeometry(0.25, 0.06, 6, 16), C.cyan, 0.5, 1.3, 0.2);
        put(g, new THREE.CylinderGeometry(0.05, 0.05, 0.4, 5), C.gray, 0.78, 1.0, 0.2, { rz: 0.7 });
        break;
      case 'permits':
        box(g, 0.55, 0.16, 0.42, C.med, 0, 0.92, 0);
        put(g, new THREE.CylinderGeometry(0.08, 0.1, 0.3, 6), C.gray, 0, 1.23, 0);
        put(g, new THREE.SphereGeometry(0.15, 8, 6), C.gray, 0, 1.45, 0);
        break;
      case 'verdict':
        put(g, new THREE.CylinderGeometry(0.48, 0.48, 0.24, 8, 1, true), C.gold, 0, 1.05, 0, { side: THREE.DoubleSide });
        for (var i = 0; i < 6; i++) {
          var a = i * PI / 3;
          put(g, new THREE.ConeGeometry(0.09, 0.22, 4), C.gold, Math.cos(a) * 0.46, 1.27, Math.sin(a) * 0.46);
        }
        break;
      default: break;
    }
    return g;
  }

  // ---------- thumbnails (one shared renderer) ----------
  var thumbR = null, thumbCache = {};
  function thumbRenderer() {
    if (thumbR) return thumbR;
    if (!ok()) return null;
    try {
      thumbR = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
      thumbR.setClearColor(0x000000, 0);
    } catch (e) { thumbR = null; warn(e); }
    return thumbR;
  }
  function thumb(kind, opts) {
    opts = opts || {};
    kind = String(kind || 'unknown');
    var size = Math.max(16, Math.min(1024, Number(opts.size) || 160));
    var key = kind + '|' + size;
    if (thumbCache[key]) return thumbCache[key];
    var r = thumbRenderer();
    if (!r) return null;
    var scene = new THREE.Scene(), obj, dir;
    lights(scene);
    if (kind.indexOf('prop:') === 0) { obj = makeProp(kind.slice(5)); dir = new THREE.Vector3(0.9, 0.65, 1); }
    else if (kind.indexOf('agent:') === 0) { obj = makeAgent(kind.slice(6)); dir = new THREE.Vector3(0.35, 0.22, 1); }
    else { obj = makeBuilding(kind); dir = new THREE.Vector3(1, 0.8, 1); }
    scene.add(obj);
    var cam = new THREE.PerspectiveCamera(28, 1, 0.1, 1000);
    fitCamera(cam, obj, dir, kind.indexOf('agent:') === 0 ? 1.02 : 1.06);
    r.setPixelRatio(PR());
    r.setSize(size, size, false);
    r.render(scene, cam);
    var url = r.domElement.toDataURL('image/png');
    disposeTree(scene);
    thumbCache[key] = url;
    return url;
  }

  // ---------- live canvas with orbit, drag, visibility ----------
  function live(el, o) {
    if (!el || !ok()) return null;
    var r;
    try { r = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch (e) { warn(e); return null; }
    r.setPixelRatio(PR());
    r.setClearColor(0x000000, 0);
    var cv = r.domElement;
    cv.style.cssText = 'display:block;width:100%;height:100%;touch-action:none;cursor:grab;outline:none';
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    if (!el.clientHeight) el.style.height = (o.defaultHeight || 320) + 'px';
    el.appendChild(cv);
    var scene = new THREE.Scene();
    var cam = new THREE.PerspectiveCamera(o.fov || 40, 1, 0.1, 5000);
    var S = {
      az: o.az == null ? 0.6 : o.az, el: o.elev == null ? 0.8 : o.elev, target: new THREE.Vector3(),
      radius: 10, dist: 20, last: -1e9, drag: null, visible: true, dead: false, speed: o.speed || 0.12
    };
    var api = { scene: scene, camera: cam, renderer: r, el: el, canvas: cv, overlays: [], onFrame: null, onClick: null, onHover: null };

    function place() {
      var ce = Math.cos(S.el);
      cam.position.set(S.target.x + S.dist * ce * Math.sin(S.az), S.target.y + S.dist * Math.sin(S.el),
        S.target.z + S.dist * ce * Math.cos(S.az));
      cam.lookAt(S.target);
    }
    function fit() {
      var vf = cam.fov * PI / 360, hf = Math.atan(Math.tan(vf) * cam.aspect);
      S.dist = S.radius / Math.sin(Math.min(vf, hf)) * (o.margin || 1.05);
      cam.near = Math.max(0.05, S.dist / 300); cam.far = S.dist * 12;
      cam.updateProjectionMatrix();
    }
    function resize() {
      var w = el.clientWidth || 320, h = el.clientHeight || 240;
      r.setSize(w, h, false);
      cam.aspect = w / h;
      fit();
    }
    api.frame = function (target, radius) { S.target.copy(target); S.radius = Math.max(radius, 0.5); fit(); };
    api.ndc = function (ev) {
      var b = cv.getBoundingClientRect();
      return new THREE.Vector2(((ev.clientX - b.left) / b.width) * 2 - 1, -((ev.clientY - b.top) / b.height) * 2 + 1);
    };
    api.project = function (v) { // world -> css px within el
      var p = v.clone().project(cam);
      return { x: (p.x + 1) / 2 * el.clientWidth, y: (1 - p.y) / 2 * el.clientHeight, behind: p.z > 1 };
    };

    function down(ev) {
      S.drag = { x: ev.clientX, y: ev.clientY, moved: 0 };
      try { cv.setPointerCapture(ev.pointerId); } catch (_) { /* ignore */ }
      cv.style.cursor = 'grabbing';
    }
    function move(ev) {
      if (S.drag) {
        var dx = ev.clientX - S.drag.x, dy = ev.clientY - S.drag.y;
        S.drag.x = ev.clientX; S.drag.y = ev.clientY; S.drag.moved += Math.abs(dx) + Math.abs(dy);
        S.az -= dx * 0.008;
        S.el = Math.max(0.15, Math.min(1.45, S.el + dy * 0.006));
        S.last = performance.now();
      } else if (api.onHover) { try { api.onHover(api.ndc(ev)); } catch (e) { warn(e); } }
    }
    function up(ev) {
      var d = S.drag;
      S.drag = null;
      cv.style.cursor = 'grab';
      if (d && d.moved < 6 && api.onClick) { try { api.onClick(api.ndc(ev)); } catch (e) { warn(e); } }
    }
    cv.addEventListener('pointerdown', down);
    cv.addEventListener('pointermove', move);
    cv.addEventListener('pointerup', up);
    cv.addEventListener('pointercancel', function () { S.drag = null; });
    cv.addEventListener('pointerleave', function () { if (!S.drag && api.onHover) api.onHover(null); });

    var ro = null, io = null;
    if (window.ResizeObserver) { ro = new ResizeObserver(function () { if (!S.dead) resize(); }); ro.observe(el); }
    if (window.IntersectionObserver) {
      io = new IntersectionObserver(function (es) { S.visible = es[es.length - 1].isIntersecting; });
      io.observe(el);
    }
    var raf = 0, prev = performance.now();
    function tick(now) {
      if (S.dead) return;
      raf = requestAnimationFrame(tick);
      var dt = Math.min(0.05, Math.max(0, (now - prev) / 1000));
      prev = now;
      if (!S.visible || document.hidden) return;
      if (!S.drag && now - S.last > 2500) S.az += S.speed * dt;
      place();
      if (api.onFrame) { try { api.onFrame(now / 1000, dt); } catch (e) { warn(e); } }
      r.render(scene, cam);
    }
    api.start = function () { resize(); place(); r.render(scene, cam); raf = requestAnimationFrame(tick); };
    api.dispose = function () {
      if (S.dead) return;
      S.dead = true;
      cancelAnimationFrame(raf);
      if (ro) ro.disconnect();
      if (io) io.disconnect();
      try { disposeTree(scene); r.dispose(); r.forceContextLoss(); } catch (e) { warn(e); }
      if (cv.parentNode) cv.parentNode.removeChild(cv);
      api.overlays.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    };
    api.overlay = function (css) {
      var d = document.createElement('div');
      d.style.cssText = 'position:absolute;pointer-events:none;color:#E8EAED;font:12px/1.35 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;' + (css || '');
      el.appendChild(d);
      api.overlays.push(d);
      return d;
    };
    return api;
  }

  // ---------- Houston map ----------
  var LAT0 = 29.7604, LON0 = -95.3698, MI_LAT = 69.0, MI_LON = 69.17 * Math.cos(LAT0 * PI / 180);
  function proj(lat, lon) { return { x: (lon - LON0) * MI_LON, z: -(lat - LAT0) * MI_LAT }; }

  function ribbon(parent, pts, width, color, opacity) {
    for (var i = 0; i < pts.length - 1; i++) {
      var a = pts[i], b = pts[i + 1], dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz);
      var m = new THREE.Mesh(new THREE.PlaneGeometry(len, width), basic(color, opacity, true));
      m.rotation.x = -PI / 2;
      m.rotation.z = -Math.atan2(dz, dx);
      m.position.set((a[0] + b[0]) / 2, 0.07, (a[1] + b[1]) / 2);
      parent.add(m);
    }
  }
  function ring(parent, cx, cz, r, w, color, opacity) {
    var m = new THREE.Mesh(new THREE.RingGeometry(r - w / 2, r + w / 2, 96), basic(color, opacity, true));
    m.rotation.x = -PI / 2;
    m.position.set(cx, 0.08, cz);
    parent.add(m);
    return m;
  }

  function buildHouston(scene) {
    var world = new THREE.Group(), rand = rng(7), i;
    scene.add(world);
    var G = 150;
    var pg = new THREE.PlaneGeometry(G * 2, G * 2, 90, 90);
    var pos = pg.attributes.position;
    for (i = 0; i < pos.count; i++) {
      var x = pos.getX(i), y = pos.getY(i), r = Math.hypot(x, y);
      var amp = r < 30 ? 0.06 : Math.min(1.4, (r - 30) * 0.04);
      pos.setZ(i, (rand() - 0.5) * amp + (r > 36 ? Math.sin(x * 0.11) * Math.cos(y * 0.09) * amp : 0));
    }
    pg.computeVertexNormals();
    var ground = new THREE.Mesh(pg, mat(C.panel, { shine: 4 }));
    ground.rotation.x = -PI / 2;
    world.add(ground);
    // Galveston Bay hint to the southeast
    var bay = new THREE.Mesh(new THREE.CircleGeometry(14, 9), basic(0x05203d, 0.85));
    bay.rotation.x = -PI / 2; bay.position.set(32, 0.03, 26); world.add(bay);

    var grid = new THREE.GridHelper(G * 2, 150, grey(C.med), grey(C.med));
    grid.material.transparent = true; grid.material.opacity = 0.06; grid.material.depthWrite = false;
    grid.position.y = 0.05;
    world.add(grid);

    ring(world, -1.5, 0.3, 5.2, 0.2, C.med, 0.6);      // I-610 loop (approx.)
    ring(world, -2.5, 0.5, 12.5, 0.22, C.med, 0.5);     // Beltway 8 (approx.)
    ring(world, -4, 1, 25, 0.2, C.med, 0.22);           // Grand Parkway (approx.)
    var hw = [
      [[-38, -1], [-12, 0.4], [0, 0], [14, -1.5], [36, -2]],   // I-10
      [[0, 0], [-3, -12], [-7, -30], [-9, -42]],             // I-45 north
      [[0, 0], [8, 9], [20, 24], [30, 34]],                   // I-45 south
      [[0, 0], [-9, 5], [-22, 16], [-32, 24]],                // I-69 southwest
      [[0, 0], [6, -10], [16, -26], [22, -36]],               // I-69 northeast
      [[0, 0], [-10, -6], [-24, -17], [-36, -26]],            // US-290
      [[0, 0], [0.5, 12], [1, 30]]                            // SH-288
    ];
    hw.forEach(function (p) { ribbon(world, p, 0.16, C.med, 0.3); });

    // city blocks: one instanced mesh
    var N = 520, blocks = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0),
      mat(0x16304f, { shine: 8 }), N);
    var m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), e = new THREE.Euler();
    for (i = 0; i < N; i++) {
      var rr = 30 * Math.pow(rand(), 1.5), a = rand() * 2 * PI;
      var w = 0.25 + rand() * 0.55, h = 0.06 + rand() * 0.25 + 2.2 * Math.exp(-rr / 2.2) * rand();
      p.set(Math.cos(a) * rr - 1.5, 0, Math.sin(a) * rr);
      s.set(w, h, w * (0.6 + rand() * 0.8));
      q.setFromEuler(e.set(0, rand() * PI, 0));
      blocks.setMatrixAt(i, m4.compose(p, q, s));
    }
    blocks.instanceMatrix.needsUpdate = true;
    world.add(blocks);
    // downtown towers
    for (i = 0; i < 9; i++) {
      var aa = rand() * 2 * PI, d = rand() * 0.7;
      box(world, 0.35, 1.4 + rand() * 2.6, 0.35, C.wall2, Math.cos(aa) * d, 0, Math.sin(aa) * d,
        { emissive: C.blue, ei: 0.25, eo: 0.5 });
    }
    return world;
  }

  function map(el, o) {
    o = o || {};
    var L = live(el, { fov: 38, elev: 0.95, az: 0.35, speed: 0.06, defaultHeight: 360 });
    if (!L) return null;
    var scene = L.scene;
    lights(scene);
    scene.fog = new THREE.Fog(BG, 60, 160);
    buildHouston(scene);
    var pinGroup = new THREE.Group();
    scene.add(pinGroup);
    var pins = {}, hits = [], selected = null, hovered = null;
    var label = L.overlay('padding:4px 8px;border-radius:6px;background:rgba(22,24,28,.88);border:1px solid rgba(255,255,255,.14);white-space:nowrap;transform:translate(-50%,-140%);display:none;z-index:2');
    var ray = new THREE.Raycaster();
    var colOf = function (c) { try { return grey(c == null ? C.med : c); } catch (e) { return grey(C.med); } };

    function clearPins() {
      disposeTree(pinGroup);
      while (pinGroup.children.length) pinGroup.remove(pinGroup.children[0]);
      pins = {}; hits = [];
    }
    function styleAll() {
      Object.keys(pins).forEach(function (id) {
        var P = pins[id], sel = selected != null && String(selected) === id, dim = selected != null && !sel;
        var h = sel ? 2.8 : 1.6;
        P.col.scale.y = h; P.col.position.y = h / 2;
        P.glow.scale.y = h; P.glow.position.y = h / 2;
        P.cap.position.y = h + 0.18;
        var color = sel ? grey(C.cyan) : P.color;
        [P.col, P.cap, P.base].forEach(function (m) { m.material.color.copy(color); });
        P.glow.material.color.copy(color);
        P.col.material.opacity = dim ? 0.3 : 0.95;
        P.cap.material.opacity = dim ? 0.3 : 1;
        P.glow.visible = false;
        P.base.material.opacity = dim ? 0.15 : 0.6;
      });
    }
    function setPins(list) {
      clearPins();
      var minX = 0, maxX = 0, minZ = 0, maxZ = 0;
      (list || []).forEach(function (pin) {
        if (pin == null || !isFinite(pin.lat) || !isFinite(pin.lon)) return;
        var id = String(pin.id), xz = proj(+pin.lat, +pin.lon), g = new THREE.Group();
        g.position.set(xz.x, 0, xz.z);
        var color = colOf(pin.color);
        var col = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 1, 8), basic(color, 0.95));
        var glow = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 1, 10, 1, true), basic(color, 0.18, true));
        var cap = new THREE.Mesh(new THREE.OctahedronGeometry(0.24, 0), basic(color, 0.999));
        var base = new THREE.Mesh(new THREE.RingGeometry(0.28, 0.5, 20), basic(color, 0.6, true));
        base.rotation.x = -PI / 2; base.position.y = 0.1;
        var hit = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 3.6, 6), new THREE.MeshBasicMaterial({ visible: false }));
        hit.position.y = 1.8; hit.userData.id = id;
        g.add(col, glow, cap, base, hit);
        pinGroup.add(g);
        pins[id] = { pin: pin, g: g, col: col, glow: glow, cap: cap, base: base, color: color };
        hits.push(hit);
        minX = Math.min(minX, xz.x); maxX = Math.max(maxX, xz.x); minZ = Math.min(minZ, xz.z); maxZ = Math.max(maxZ, xz.z);
      });
      var center = new THREE.Vector3((minX + maxX) / 2, 0, (minZ + maxZ) / 2);
      var radius = Math.max(7, Math.hypot(maxX - minX, maxZ - minZ) / 2 + 2.5);
      var k = Math.max(1, radius / 6.5);
      Object.keys(pins).forEach(function (id) { pins[id].g.scale.set(k, k, k); });
      L.frame(center, radius * 0.92);
      scene.fog.near = radius * 2.6; scene.fog.far = radius * 5.5;
      if (selected != null && !pins[String(selected)]) selected = null;
      styleAll();
    }
    function pick(ndc) {
      if (!ndc || !hits.length) return null;
      ray.setFromCamera(ndc, L.camera);
      var h = ray.intersectObjects(hits, false);
      return h.length ? h[0].object.userData.id : null;
    }
    L.onClick = function (ndc) {
      var id = pick(ndc);
      if (id == null) return;
      api.select(id);
      if (o.onPick) o.onPick(pins[id] ? pins[id].pin.id : id);
    };
    L.onHover = function (ndc) {
      hovered = pick(ndc);
      L.canvas.style.cursor = hovered != null ? 'pointer' : 'grab';
    };
    var top = new THREE.Vector3();
    L.onFrame = function (t) {
      Object.keys(pins).forEach(function (id) {
        var P = pins[id], sel = selected != null && String(selected) === id;
        var k = sel ? 1 + 0.35 * (0.5 + 0.5 * Math.sin(t * 3)) : 1;
        P.base.scale.set(k, k, k);
        P.cap.rotation.y = t * (sel ? 1.6 : 0.6);
      });
      var show = hovered != null ? hovered : (selected != null ? String(selected) : null);
      var P = show != null ? pins[show] : null;
      if (P && P.pin.label) {
        top.set(P.g.position.x, (P.cap.position.y + 0.3) * P.g.scale.y, P.g.position.z);
        var sp = L.project(top);
        label.textContent = P.pin.label;
        label.style.left = sp.x + 'px'; label.style.top = sp.y + 'px';
        label.style.display = sp.behind ? 'none' : 'block';
      } else label.style.display = 'none';
    };
    var api = {
      setPins: safe(function (list) { setPins(list); }),
      select: safe(function (id) { selected = id == null ? null : String(id); styleAll(); }),
      dispose: safe(function () { L.dispose(); })
    };
    setPins(o.pins || []);
    L.start();
    return api;
  }

  // ---------- the listed space, to scale ----------
  function Instancer(parent) {
    var groups = {}, UB = null, UC = null;
    function unitBox() { return UB || (UB = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0)); }
    function unitCyl() { return UC || (UC = new THREE.CylinderGeometry(1, 1, 1, 10).translate(0, 0.5, 0)); }
    return {
      // kind 'b' box (w,h,d) or 'c' cylinder (radius, h, radius); base at y; rotation about y
      add: function (kind, color, x, y, z, w, h, d, ry, o) {
        o = o || {};
        var key = kind + '|' + color + '|' + (o.opacity || 1) + '|' + (o.emissive == null ? '' : o.emissive);
        var g = groups[key] || (groups[key] = { geo: kind === 'c' ? unitCyl() : unitBox(), mat: mat(color, o), list: [] });
        if (g.list.length < 4000) g.list.push([x, y, z, w, h, d, ry || 0]);
      },
      done: function () {
        var m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), e = new THREE.Euler();
        Object.keys(groups).forEach(function (k) {
          var g = groups[k];
          if (!g.list.length) return;
          var im = new THREE.InstancedMesh(g.geo, g.mat, g.list.length);
          g.list.forEach(function (t, i) {
            p.set(t[0], t[1], t[2]); s.set(t[3], t[4], t[5]); q.setFromEuler(e.set(0, t[6], 0));
            im.setMatrixAt(i, m4.compose(p, q, s));
          });
          im.instanceMatrix.needsUpdate = true;
          if (g.mat.transparent) im.renderOrder = 2;
          parent.add(im);
        });
      }
    };
  }

  function fillSpace(I, seg, biz, W, D, H) {
    var x, z, i, n, xL = -W / 2, xR = W / 2, zB = -D / 2, zF = D / 2;
    var F = function (k, c, x, y, z, w, h, d, ry, o) { I.add(k, c, x, y, z, w, h, d, ry, o); };
    var reception = function () { if (W > 16 && D > 14) F('b', C.wall2, xR - 5, 0, zF - 4, 6, 3.5, 2.5); };
    var gridEach = function (x0, x1, z0, z1, sx, sz, fn) {
      for (var zz = z0; zz <= z1 + 1e-6; zz += sz) for (var xx = x0; xx <= x1 + 1e-6; xx += sx) fn(xx, zz);
    };
    var info = {};
    switch (biz) {
      case 'indoor_pickleball': {
        var a = Math.floor(W / 30) * Math.floor(D / 60), b = Math.floor(W / 60) * Math.floor(D / 30);
        var rot = b > a, cw = rot ? 60 : 30, cd = rot ? 30 : 60;
        var nx = Math.floor(W / cw), nz = Math.floor(D / cd);
        info.courts = nx * nz;
        if (!info.courts) break;
        var R = function (cx, cz, lx, lz) { return rot ? [cx + lz, cz - lx] : [cx + lx, cz + lz]; };
        var line = function (cx, cz, x1, z1, x2, z2) { var p = R(cx, cz, x1, z1), q = R(cx, cz, x2, z2); seg.push(p[0], 0.25, p[1], q[0], 0.25, q[1]); };
        for (i = 0; i < nx; i++) for (var j = 0; j < nz; j++) {
          var cx = -nx * cw / 2 + cw / 2 + i * cw, cz = -nz * cd / 2 + cd / 2 + j * cd;
          F('b', 0x0b2a4a, cx, 0.02, cz, cw - 1, 0.08, cd - 1);
          F('b', C.blue, cx, 0.1, cz, rot ? 44 : 20, 0.08, rot ? 20 : 44);
          line(cx, cz, -10, -22, 10, -22); line(cx, cz, 10, -22, 10, 22); line(cx, cz, 10, 22, -10, 22); line(cx, cz, -10, 22, -10, -22);
          line(cx, cz, -10, -7, 10, -7); line(cx, cz, -10, 7, 10, 7);
          line(cx, cz, 0, -22, 0, -7); line(cx, cz, 0, 7, 0, 22);
          F('b', C.light, cx, 0.1, cz, rot ? 0.3 : 21, 3, rot ? 21 : 0.3, 0, { opacity: 0.55 });
        }
        break;
      }
      case 'salon_barber': {
        var rows = D >= 26 ? [zB + 4, zF - 4] : [zB + 4];
        rows.forEach(function (rz, k) {
          var wallZ = k ? zF - 0.4 : zB + 0.2, back = k ? -1 : 1;
          for (x = xL + 5; x <= xR - 7; x += 6) {
            F('c', C.gray, x, 0, rz, 0.9, 0.3, 0.9);
            F('c', C.gray, x, 0.3, rz, 0.15, 1.0, 0.15);
            F('b', C.blue, x, 1.3, rz, 2, 0.5, 2);
            F('b', C.blue, x, 1.8, rz + back * 0.9, 2, 2, 0.35);
            F('b', C.light, x, 2.6, wallZ, 2.6, 3.6, 0.15, 0, { emissive: C.light });
          }
        });
        for (z = zB + 3; z <= Math.min(zB + 9, zF - 3); z += 3) F('b', C.cyan, xR - 2, 0, z, 2.2, 3, 2);
        reception();
        break;
      }
      case 'cafe': case 'restaurant': case 'fast_food': case 'bar': {
        var isBar = biz === 'bar';
        var cl = Math.max(6, Math.min(W - 6, isBar ? W * 0.75 : Math.max(12, W * 0.4)));
        var ccx = isBar ? 0 : xR - 3 - cl / 2;
        F('b', C.blue, ccx, 0, zB + 1, cl, 6, 1.2);
        F('b', C.wall2, ccx, 0, zB + 4.5, cl, 3.5, 3);
        F('b', C.light, ccx, 3.5, zB + 4.5, cl + 0.3, 0.2, 3.3);
        if (isBar) for (x = ccx - cl / 2 + 1.5; x <= ccx + cl / 2 - 1; x += 2.6) F('c', C.gray, x, 0, zB + 7.3, 0.6, 2.6, 0.6);
        var st = biz === 'restaurant' ? 9 : 8;
        gridEach(xL + 4.5, xR - 4.5, zB + (isBar ? 13 : 11), zF - 4, st, st, function (tx, tz) {
          F('c', C.cyan, tx, 2.4, tz, 1.5, 0.15, 1.5);
          F('c', C.gray, tx, 0, tz, 0.15, 2.4, 0.15);
          F('b', C.blue, tx - 2.5, 0, tz, 1.3, 1.5, 1.3);
          F('b', C.blue, tx + 2.5, 0, tz, 1.3, 1.5, 1.3);
          F('b', C.blue, tx - 3.1, 1.5, tz, 0.2, 1.6, 1.3);
          F('b', C.blue, tx + 3.1, 1.5, tz, 0.2, 1.6, 1.3);
        });
        break;
      }
      case 'yoga_pilates':
        n = 0;
        gridEach(xL + 3, xR - 3, zB + 4, zF - 9, 4.5, 8, function (mx, mz) { F('b', (n++) % 2 ? C.med : C.blue, mx, 0, mz, 2.2, 0.12, 6); });
        F('b', C.light, 0, 0.5, zB + 0.2, W - 2, 7, 0.15, 0, { opacity: 0.5, emissive: C.light });
        reception();
        break;
      case 'dance_studio':
        F('b', 0x1d3a5a, 0, 0, 0, W - 2, 0.08, D - 2);
        F('b', C.light, 0, 0.5, zB + 0.2, W - 2, 7, 0.15, 0, { opacity: 0.5, emissive: C.light });
        F('b', C.gray, 0, 3.4, zB + 1.2, W - 4, 0.15, 0.15);
        reception();
        break;
      case 'martial_arts':
        n = 0;
        gridEach(xL + 6, xR - 8, zB + 4, zF - 6, 5, 5, function (mx, mz) { F('b', (n++) % 2 ? C.blue : C.med, mx, 0, mz, 5, 0.15, 5); });
        for (z = zB + 4; z <= zF - 5; z += 6) {
          F('c', C.gray, xR - 3, 2, z, 0.7, 3.6, 0.7);
          F('b', C.gray, xR - 3, 5.6, z, 0.1, 2, 0.1);
        }
        break;
      case 'fitness_gym':
        for (x = xL + 3; x <= xR - 3; x += 4) {
          F('b', C.gray, x, 0, zB + 5, 2.8, 0.7, 6.5);
          F('b', C.light, x, 0.7, zB + 1.9, 2.4, 3.8, 0.4, 0, { emissive: C.light });
        }
        if (D >= 30) for (x = xL + 7; x <= xR - 7; x += 12) {
          var rz = zB + 16;
          [[-2, -2], [2, -2], [-2, 2], [2, 2]].forEach(function (pp) { F('b', C.med, x + pp[0], 0, rz + pp[1], 0.3, 7.5, 0.3); });
          F('b', C.med, x, 7.3, rz - 2, 4.3, 0.3, 0.3); F('b', C.med, x, 7.3, rz + 2, 4.3, 0.3, 0.3);
          F('b', C.cyan, x, 4.5, rz, 7, 0.15, 0.15);
          F('b', C.blue, x, 0, rz, 1.2, 1.5, 4);
        }
        if (D >= 42) for (x = xL + 5; x <= xR - 5; x += 6) F('b', C.blue, x, 0, zF - 8, 1.3, 1.5, 4.2);
        F('b', C.gray, xL + 1.5, 0, 0, 2, 3, Math.max(4, Math.min(D - 14, 22)));
        break;
      case 'childcare': case 'tutoring': {
        var rooms = biz === 'childcare' && W >= 30 && D >= 34;
        if (rooms) {
          var rw = 25, rd = 24, cnt = Math.min(10, Math.floor((W - 2) / rw)), x0 = -cnt * rw / 2;
          for (i = 0; i < cnt; i++) {
            var lx = x0 + i * rw;
            F('b', C.light, lx, 0, zB + rd / 2, 0.3, 4, rd, 0, { opacity: 0.35 });
            if (i === cnt - 1) F('b', C.light, lx + rw, 0, zB + rd / 2, 0.3, 4, rd, 0, { opacity: 0.35 });
            F('b', C.light, lx + rw * 0.3, 0, zB + rd, rw * 0.6, 4, 0.3, 0, { opacity: 0.35 });
            [[-5, -6], [5, -6], [0, 3]].forEach(function (tp) {
              var tx = lx + rw / 2 + tp[0], tz = zB + rd / 2 + tp[1];
              F('b', C.cyan, tx, 0, tz, 5, 1.8, 2.5);
              F('b', C.blue, tx - 1.5, 0, tz + 2, 1, 1, 1); F('b', C.blue, tx + 1.5, 0, tz + 2, 1, 1, 1);
            });
          }
          n = 0;
          gridEach(xL + 6, xR - 10, zB + rd + 6, zF - 5, 9, 8, function (mx, mz) { F('b', [C.med, C.light, C.blue][(n++) % 3], mx, 0, mz, 5, 0.15, 5); });
        } else {
          var low = biz === 'childcare';
          gridEach(xL + 5, xR - 5, zB + 5, zF - 5, 10, 9, function (tx, tz) {
            F('b', C.cyan, tx, 0, tz, low ? 5 : 6, low ? 1.8 : 2.5, low ? 2.5 : 3);
            F('b', C.blue, tx - 1.7, 0, tz + 2.3, 1.2, 1.2, 1.2); F('b', C.blue, tx + 1.7, 0, tz + 2.3, 1.2, 1.2, 1.2);
            F('b', C.blue, tx - 1.7, 0, tz - 2.3, 1.2, 1.2, 1.2); F('b', C.blue, tx + 1.7, 0, tz - 2.3, 1.2, 1.2, 1.2);
          });
        }
        if (biz === 'tutoring') F('b', C.cyan, 0, 3, zB + 0.2, Math.min(W - 4, 16), 4, 0.12, 0, { emissive: C.cyan, ei: 0.3 });
        reception();
        break;
      }
      case 'physical_therapy': case 'medical_clinic': case 'dental': case 'veterinary': {
        var rw2 = 10, rd2 = 12, rowsZ = [1];
        if (biz !== 'physical_therapy' && D >= 2 * rd2 + 8) rowsZ.push(-1);
        rowsZ.forEach(function (sgn) {
          var wall = sgn > 0 ? zB : zF;
          var mid = wall + sgn * rd2 / 2, front = wall + sgn * rd2;
          var count = Math.min(30, Math.floor((W - 4) / rw2)), sx0 = -count * rw2 / 2;
          for (i = 0; i <= count; i++) F('b', C.light, sx0 + i * rw2, 0, mid, 0.25, 8, rd2, 0, { opacity: 0.28 });
          for (i = 0; i < count; i++) {
            var rx = sx0 + i * rw2;
            F('b', C.light, rx + rw2 * 0.35, 0, front, rw2 * 0.7, 8, 0.25, 0, { opacity: 0.28 });
            F('b', C.cyan, rx + rw2 / 2, 0, mid - sgn * 1, 2.5, 2.8, 6);
          }
        });
        if (biz === 'physical_therapy')
          gridEach(xL + 5, xR - 12, zB + rd2 + 6, zF - 5, 8, 10, function (tx, tz) { F('b', C.cyan, tx, 0, tz, 2.5, 2.4, 6.5); });
        reception();
        break;
      }
      case 'laundromat':
        for (x = xL + 2; x <= xR - 2; x += 2.7) F('b', C.light, x, 0, zB + 1.5, 2.5, 6, 2.6);
        for (z = zB + 9; z <= zF - 5; z += 12) for (x = xL + 4; x <= xR - 4; x += 2.7) {
          F('b', C.cyan, x, 0, z - 1.3, 2.5, 3.2, 2.5); F('b', C.cyan, x, 0, z + 1.3, 2.5, 3.2, 2.5);
        }
        break;
      case 'coworking':
        gridEach(xL + 7, xR - 9, zB + 5, zF - 5, 14, 9, function (tx, tz) {
          F('b', C.light, tx, 2.4, tz, 10, 0.15, 5);
          F('b', C.gray, tx - 4.5, 0, tz, 0.3, 2.4, 4.5); F('b', C.gray, tx + 4.5, 0, tz, 0.3, 2.4, 4.5);
          for (var k = -1; k <= 1; k++) { F('b', C.blue, tx + k * 3, 0, tz - 3.4, 1.5, 1.6, 1.5); F('b', C.blue, tx + k * 3, 0, tz + 3.4, 1.5, 1.6, 1.5); }
        });
        for (z = zB + 3; z <= zF - 3; z += 5) F('b', C.blue, xR - 2.2, 0, z, 3.5, 7.5, 3.5, 0, { opacity: 0.6 });
        break;
      case 'auto_repair':
        for (x = xL + 8; x <= xR - 7; x += 14) {
          F('b', C.med, x - 5, 0, zB + 13, 0.6, 10, 0.6); F('b', C.med, x + 5, 0, zB + 13, 0.6, 10, 0.6);
          F('b', C.blue, x, 4.5, zB + 13, 6, 3, 14);
          F('b', C.gray, x, 0, zB + 13, 9, 0.1, 22);
        }
        F('b', C.gray, xL + 2, 0, zF - 6, 2.5, 6, Math.min(D - 8, 16));
        break;
      case 'self_storage':
        gridEach(xL + 6, xR - 6, zB + 6, zF - 6, 15, 15, function (ux, uz) { F('b', C.wall2, ux, 0, uz, 9.6, Math.min(8, H - 1), 9.6); });
        break;
      case 'car_wash': {
        var tl = Math.max(10, Math.min(W - 6, 110));
        F('b', C.blue, 0, 0, 0, tl, Math.min(12, H - 1), 16, 0, { opacity: 0.35 });
        for (x = -tl / 2 + 8; x <= tl / 2 - 8; x += 14) { F('c', C.med, x, 0, -5, 1.2, 9, 1.2); F('c', C.med, x, 0, 5, 1.2, 9, 1.2); }
        break;
      }
      case 'climbing_gym': {
        var wh = Math.max(6, Math.min(H - 1, 40)), rr = rng(3);
        F('b', C.blue, 0, 0, zB + 1.5, W - 4, wh, 2);
        for (i = 0; i < Math.min(400, W * wh / 6); i++)
          F('b', [C.med, C.light, C.gold, C.cyan][i % 4], (rr() - 0.5) * (W - 6), 1 + rr() * (wh - 2), zB + 2.6, 0.7, 0.5, 0.4);
        F('b', C.gray, 0, 0, zB + 7, W - 4, 0.8, 8);
        break;
      }
      default: { // retail-style shelving
        var len = Math.max(6, Math.min(W - 14, 48)), gx = xL + 3 + len / 2;
        for (z = zB + 6; z <= zF - 10; z += 9) {
          F('b', C.wall2, gx, 0, z, len, 6, 3);
          F('b', C.light, gx, 6, z, len, 0.15, 3.1, 0, { emissive: C.light, ei: 0.25 });
        }
        if (W > 20) for (z = zF - 12; z <= zF - 4; z += 6) F('b', C.blue, xR - 5, 0, z, 6, 3.3, 2.5);
      }
    }
    return info;
  }

  function space(el, o) {
    o = o || {};
    var sf = Number(o.sf);
    if (!(sf > 0)) return null;
    var W = Math.sqrt(sf * 1.6), D = Math.sqrt(sf / 1.6);
    var known = Number(o.ceiling_ft) > 0, H = known ? Number(o.ceiling_ft) : 14;
    var L = live(el, { fov: 34, elev: 0.72, az: 0.65, speed: 0.1, margin: 1.02, defaultHeight: 300 });
    if (!L) return null;
    var scene = L.scene, root = new THREE.Group(), i;
    scene.add(root);
    lights(scene);

    root.add(new THREE.Mesh(new THREE.BoxGeometry(W, 0.3, D).translate(0, -0.15, 0), mat(C.floor, { shine: 4 })));
    var walls = new THREE.Mesh(new THREE.BoxGeometry(W, H, D).translate(0, H / 2, 0),
      mat(C.blue, { opacity: 0.07, side: THREE.DoubleSide }));
    walls.renderOrder = 3;
    root.add(walls);

    // floor grid every 10 ft
    var gp = [];
    for (var gx = -W / 2 + 10; gx < W / 2; gx += 10) gp.push(gx, 0.01, -D / 2, gx, 0.01, D / 2);
    for (var gz = -D / 2 + 10; gz < D / 2; gz += 10) gp.push(-W / 2, 0.01, gz, W / 2, 0.01, gz);
    var lineSeg = function (arr, color, opacity) {
      var g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
      return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: grey(color), transparent: true, opacity: opacity }));
    };
    if (gp.length) root.add(lineSeg(gp, C.med, 0.1));

    // walls outline: bottom + verticals solid, top dashed when the ceiling height is unknown
    var w2 = W / 2, d2 = D / 2, corners = [[-w2, -d2], [w2, -d2], [w2, d2], [-w2, d2]], ep = [];
    for (i = 0; i < 4; i++) {
      var a = corners[i], b = corners[(i + 1) % 4];
      ep.push(a[0], 0, a[1], b[0], 0, b[1]);
      ep.push(a[0], 0, a[1], a[0], H, a[1]);
    }
    root.add(lineSeg(ep, C.med, 0.8));
    var topPts = corners.concat([corners[0]]).map(function (c) { return new THREE.Vector3(c[0], H, c[1]); });
    var topLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(topPts), known
      ? new THREE.LineBasicMaterial({ color: grey(C.med), transparent: true, opacity: 0.8 })
      : new THREE.LineDashedMaterial({ color: grey(C.cyan), dashSize: 2.5, gapSize: 2, transparent: true, opacity: 0.9 }));
    if (!known) topLine.computeLineDistances();
    root.add(topLine);

    // the business, to scale
    var I = Instancer(root), seg = [];
    var info = fillSpace(I, seg, String(o.business || ''), W, D, H) || {};
    // a 6 ft person for scale, near the front-left corner
    var hx = -w2 + 3, hz = d2 - 3;
    I.add('c', C.gold, hx - 0.35, 0, hz, 0.3, 3, 0.3); I.add('c', C.gold, hx + 0.35, 0, hz, 0.3, 3, 0.3);
    I.add('b', C.gold, hx, 3, hz, 1.4, 2.1, 0.8);
    I.done();
    var head = new THREE.Mesh(new THREE.SphereGeometry(0.45, 8, 6), mat(C.gold));
    head.position.set(hx, 5.55, hz);
    root.add(head);
    if (seg.length) root.add(lineSeg(seg, C.cyan, 0.9));

    L.frame(new THREE.Vector3(0, H * 0.3, 0), 0.5 * Math.sqrt(W * W + D * D + H * H));

    info.width_ft = Math.round(W); info.depth_ft = Math.round(D);
    info.height_ft = known ? H : null; info.height_known = known;
    info.assumed = 'Footprint shape assumed (1.6:1); area is the listed ' + Math.round(sf).toLocaleString() + ' sq ft.' +
      (known ? '' : ' Ceiling height unknown: drawn at 14 ft (dashed).');
    if (o.label != null) {
      var ov = L.overlay('left:10px;top:8px;max-width:calc(100% - 20px)');
      var t = document.createElement('div'); t.style.cssText = 'font-weight:600;font-size:13px'; t.textContent = String(o.label);
      var s2 = document.createElement('div'); s2.style.cssText = 'color:#A6ABB3;opacity:.9';
      s2.textContent = '~' + info.width_ft + ' × ' + info.depth_ft + ' ft · ' + (known ? H + ' ft ceiling' : 'ceiling unknown') +
        (info.courts != null ? ' · ' + info.courts + ' court' + (info.courts === 1 ? '' : 's') : '') + ' · person = 6 ft';
      ov.appendChild(t); ov.appendChild(s2);
    }
    L.start();
    return { dispose: safe(function () { L.dispose(); }), info: info };
  }

  window.Suite3D = {
    ok: safe(ok, false),
    thumb: safe(thumb),
    map: safe(map),
    space: safe(space)
  };
})();
