// Shared 3D kit of the films (media/pitch). The board and the clock are the
// CadQuery solids of the repository (mechanical/scenes.py --film-meshes); the
// pieces are drawn on the base diameters chessboard_calc computes, read from
// window.FACTS.scene. Everything is a pure function of the time it is given,
// so any frame renders the same on every seek.
import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const F = () => window.FACTS.scene;
const FILES = "abcdefgh";
export const clamp01 = (u) => Math.max(0, Math.min(1, u));
export const smooth = (u) => {
  const v = clamp01(u);
  return v * v * (3 - 2 * v);
};

// ---------------------------------------------------------------- stage
export function createStage(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(1080, 1920, false);
  renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x101418);
  const camera = new THREE.PerspectiveCamera(34, 1080 / 1920, 2, 8000);
  // the subject of a shot sits at y 850, the middle of the safe area
  camera.setViewOffset(1080, 1920, 0, 110, 1080, 1920);
  scene.add(new THREE.HemisphereLight(0xfff4e6, 0x1a1f26, 1.3));
  const key = new THREE.DirectionalLight(0xffffff, 2.6);
  key.position.set(-260, 560, 320);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.0004;
  Object.assign(key.shadow.camera, { left: -360, right: 360, top: 360, bottom: -360, near: 10, far: 1800 });
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x9fc4ff, 0.35);
  rim.position.set(300, 200, -400);
  scene.add(rim);
  return { renderer, scene, camera, key };
}

// CadQuery frame (x along the files, y up the ranks, z up, origin at a1's
// corner) to the scene frame (y up, centred on the play area).
function half() {
  return (F().pitch * F().grid) / 2;
}
export function cadGroup() {
  const g = new THREE.Group();
  g.rotation.x = -Math.PI / 2;
  g.position.set(-half(), 0, half());
  return g;
}
export function cadToScene(x, y, z = 0) {
  return new THREE.Vector3(x - half(), z, half() - y);
}
export function squareXZ(sq) {
  const p = F().pitch;
  const f = FILES.indexOf(sq[0]);
  const r = Number(sq.slice(1)) - 1;
  const v = cadToScene((f + 0.5) * p, (r + 0.5) * p);
  return [v.x, v.z];
}

// ---------------------------------------------------------------- meshes
const LOOK = {
  "#d38a3c": { roughness: 0.32, metalness: 0.75 }, // copper spirals
  "#f0c95a": { roughness: 0.4, emissive: 0x3a2a00 }, // LED bodies
  "#d9c19a": { roughness: 0.72 }, // plywood
  "#7a4b28": { roughness: 0.72 }, // dark veneer
  "#e9e3d6": { roughness: 0.45 }, // clock bar
};

// Load the meshes of the manifest that `keep` accepts. Returns one group per
// "set/layer", each holding a CadQuery-framed child, plus the manifest.
export async function loadMeshes(scene, keep, base = "assets/commun/meshes/") {
  const manifest = await (await fetch(base + "manifest.json")).json();
  const loader = new STLLoader();
  const layers = {};
  await Promise.all(
    manifest.meshes.filter(keep).map(
      (m) =>
        new Promise((ok, fail) =>
          loader.load(
            base + m.file,
            (geo) => {
              geo.computeVertexNormals();
              const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(m.color), roughness: 0.6, ...(LOOK[m.color] || {}) });
              const mesh = new THREE.Mesh(geo, mat);
              mesh.castShadow = true;
              mesh.receiveShadow = true;
              const key = `${m.set}/${m.layer}`;
              if (!layers[key]) {
                const outer = new THREE.Group();
                const inner = cadGroup();
                outer.add(inner);
                scene.add(outer);
                layers[key] = { outer, inner };
              }
              layers[key].inner.add(mesh);
              ok();
            },
            undefined,
            fail,
          ),
        ),
    ),
  );
  return { layers, manifest };
}

// Height of the playing surface, from the loaded plywood itself.
export function boardTop(layers) {
  const box = new THREE.Box3().setFromObject(layers["fin/bois"].outer);
  return box.max.y;
}

// ---------------------------------------------------------------- pieces
// profiles: [radius / base radius, height / piece height], bottom to top
const PROFILES = {
  pawn: [[0, 0], [1, 0], [1, 0.07], [0.9, 0.1], [0.9, 0.14], [0.66, 0.2], [0.44, 0.3], [0.34, 0.5], [0.5, 0.56], [0.5, 0.6], [0.3, 0.63], [0, 0.63]],
  rook: [[0, 0], [1, 0], [1, 0.07], [0.9, 0.11], [0.9, 0.15], [0.68, 0.22], [0.6, 0.62], [0.74, 0.7], [0.8, 0.75], [0.8, 0.86], [0.56, 0.86], [0.56, 0.8], [0, 0.8]],
  bishop: [[0, 0], [1, 0], [1, 0.06], [0.9, 0.09], [0.9, 0.13], [0.62, 0.2], [0.42, 0.36], [0.3, 0.56], [0.52, 0.6], [0.52, 0.63], [0.28, 0.65], [0, 0.65]],
  queen: [[0, 0], [1, 0], [1, 0.06], [0.9, 0.09], [0.9, 0.13], [0.6, 0.2], [0.4, 0.38], [0.28, 0.62], [0.5, 0.66], [0.5, 0.69], [0.32, 0.71], [0.5, 0.86], [0.56, 0.88], [0, 0.88]],
  king: [[0, 0], [1, 0], [1, 0.06], [0.9, 0.09], [0.9, 0.13], [0.6, 0.2], [0.4, 0.38], [0.29, 0.62], [0.52, 0.66], [0.52, 0.69], [0.33, 0.71], [0.48, 0.83], [0.5, 0.85], [0.2, 0.88], [0, 0.88]],
  knight: [[0, 0], [1, 0], [1, 0.07], [0.9, 0.1], [0.9, 0.14], [0.74, 0.2], [0.7, 0.26], [0, 0.26]],
};

export const MATERIALS = {
  ivory: new THREE.MeshStandardMaterial({ color: 0xf1e8d8, roughness: 0.42 }),
  ebony: new THREE.MeshStandardMaterial({ color: 0x1d1d1f, roughness: 0.3, metalness: 0.05 }),
  felt: new THREE.MeshStandardMaterial({ color: 0x2c3138, roughness: 1 }),
  // no environment map in these scenes: a fully metallic copper would render near black
  copper: new THREE.MeshStandardMaterial({ color: 0xc8782f, roughness: 0.35, metalness: 0.35 }),
  ferrite: new THREE.MeshStandardMaterial({ color: 0x5a636d, roughness: 0.5 }),
  ceramic: new THREE.MeshStandardMaterial({ color: 0xcfc4a8, roughness: 0.6 }),
};

// The horse head in profile, facing +x, drawn with curves: chest, throat,
// jaw, muzzle, forehead, ear, poll and mane. Extruded with a deep rounded
// bevel, then thinned towards the muzzle and the poll.
function knightHead(r, h, material) {
  const P = (u, v) => [u * r, v * h];
  const s = new THREE.Shape();
  s.moveTo(...P(-0.66, 0.24));
  s.lineTo(...P(0.56, 0.24));
  s.quadraticCurveTo(...P(0.66, 0.38), ...P(0.42, 0.5));
  s.quadraticCurveTo(...P(0.36, 0.55), ...P(0.5, 0.6));
  s.quadraticCurveTo(...P(0.78, 0.62), ...P(0.98, 0.68));
  s.quadraticCurveTo(...P(1.08, 0.73), ...P(0.98, 0.79));
  s.quadraticCurveTo(...P(0.82, 0.85), ...P(0.6, 0.87));
  s.quadraticCurveTo(...P(0.44, 0.9), ...P(0.32, 0.97));
  s.lineTo(...P(0.27, 1.07));
  s.quadraticCurveTo(...P(0.18, 1.04), ...P(0.12, 0.98));
  s.quadraticCurveTo(...P(-0.12, 0.97), ...P(-0.34, 0.86));
  s.quadraticCurveTo(...P(-0.62, 0.72), ...P(-0.66, 0.46));
  s.closePath();
  const depth = 0.48 * r;
  const geo = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: true, bevelSize: 0.15 * r, bevelThickness: 0.34 * r, bevelSegments: 10, curveSegments: 14 });
  geo.translate(0, 0, -depth / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i) / r;
    const y = pos.getY(i) / h;
    const t = (1 - 0.45 * clamp01((x - 0.15) / 0.85)) * (1 - 0.3 * clamp01((y - 0.8) / 0.25)) * (1 + 0.22 * clamp01((0.5 - y) / 0.26));
    pos.setZ(i, pos.getZ(i) * t);
  }
  geo.computeVertexNormals();
  const g = new THREE.Group();
  const head = new THREE.Mesh(geo, material);
  g.add(head);
  // the mane: a ridge of small rounded tufts along the neck
  for (let k = 0; k < 6; k++) {
    const u = k / 5;
    const tuft = new THREE.Mesh(new THREE.SphereGeometry(0.14 * r, 16, 10), material);
    tuft.scale.set(1.3, 0.8, 0.7);
    tuft.position.set((-0.6 + 0.62 * u) * r, (0.52 + 0.42 * u - 0.12 * u * u) * h, 0);
    g.add(tuft);
  }
  // eyes, a touch darker
  const eye = new THREE.MeshStandardMaterial({ color: material === MATERIALS.ivory ? 0x3a3128 : 0x5a5a5e, roughness: 0.3 });
  for (const side of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.05 * r, 12, 8), eye);
    e.position.set(0.42 * r, 0.84 * h, side * 0.27 * r);
    g.add(e);
  }
  g.traverse((m) => {
    m.castShadow = true;
    m.receiveShadow = true;
  });
  return g;
}

export function makePiece(kind, white) {
  const dims = F().pieces[kind];
  const r = dims.base / 2;
  const h = dims.height;
  const material = white ? MATERIALS.ivory : MATERIALS.ebony;
  const g = new THREE.Group();
  const add = (geo, y = 0, x = 0, z = 0) => {
    const m = new THREE.Mesh(geo, material);
    m.position.set(x, y, z);
    m.castShadow = true;
    m.receiveShadow = true;
    g.add(m);
    return m;
  };
  add(new THREE.LatheGeometry(PROFILES[kind].map(([u, v]) => new THREE.Vector2(u * r, v * h)), 72));
  if (kind === "pawn") add(new THREE.SphereGeometry(0.5 * r, 48, 24), 0.78 * h);
  if (kind === "bishop") {
    add(new THREE.SphereGeometry(0.46 * r, 48, 24), 0.8 * h).scale.set(1, 1.45, 1);
    add(new THREE.SphereGeometry(0.13 * r, 24, 12), 0.98 * h);
  }
  if (kind === "rook") {
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2 + Math.PI / 4;
      const b = add(new THREE.BoxGeometry(0.44 * r, 0.14 * h, 0.26 * r), 0.93 * h, Math.cos(a) * 0.67 * r, Math.sin(a) * 0.67 * r);
      b.rotation.y = -a + Math.PI / 2;
    }
  }
  if (kind === "queen") {
    for (let k = 0; k < 8; k++) {
      const a = (k * Math.PI) / 4;
      add(new THREE.SphereGeometry(0.1 * r, 16, 8), 0.9 * h, Math.cos(a) * 0.5 * r, Math.sin(a) * 0.5 * r);
    }
    add(new THREE.SphereGeometry(0.16 * r, 24, 12), 0.95 * h);
  }
  if (kind === "king") {
    add(new THREE.BoxGeometry(0.16 * r, 0.16 * h, 0.16 * r), 0.95 * h);
    add(new THREE.BoxGeometry(0.44 * r, 0.06 * h, 0.16 * r), 0.97 * h);
  }
  if (kind === "knight") g.add(knightHead(r, h, material));
  g.userData = { kind, white, height: h };
  return g;
}

const BACK = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"];

// The 32 pieces on their starting squares, keyed by square; knights face the
// other camp.
export function startPosition(scene, top) {
  const pieces = {};
  for (let f = 0; f < 8; f++) {
    for (const [rank, kind, white] of [[1, BACK[f], true], [2, "pawn", true], [8, BACK[f], false], [7, "pawn", false]]) {
      const sq = FILES[f] + rank;
      const p = makePiece(kind, white);
      const [x, z] = squareXZ(sq);
      p.position.set(x, top, z);
      if (kind === "knight") p.rotation.y = white ? Math.PI / 2 : -Math.PI / 2;
      scene.add(p);
      pieces[sq] = p;
    }
  }
  return pieces;
}

// ---------------------------------------------------------------- light holes
function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const x = c.getContext("2d");
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.3, "rgba(255,255,255,0.5)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g;
  x.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export const WHITE_LED = 0xfff1d6;
export const AMBER_LED = 0xffb347;

// The two light points of each square, at chessboard_calc's led_points.
export function lightHoles(scene, top) {
  const tex = glowTexture();
  const bySquare = {};
  const p = F().pitch;
  for (const [x, y] of F().led_points) {
    const sq = FILES[Math.floor(x / p)] + (Math.floor(y / p) + 1);
    const v = cadToScene(x, y, top);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    halo.position.set(v.x, top + 1.5, v.z);
    halo.scale.set(26, 26, 1);
    const core = new THREE.Mesh(new THREE.CircleGeometry(1.25, 16), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 }));
    core.rotation.x = -Math.PI / 2;
    core.position.set(v.x, top + 0.4, v.z);
    scene.add(halo, core);
    (bySquare[sq] ||= []).push({ halo, core });
  }
  return {
    clear() {
      for (const list of Object.values(bySquare)) for (const { halo, core } of list) halo.material.opacity = core.material.opacity = 0;
    },
    set(sq, hex, level) {
      for (const { halo, core } of bySquare[sq] || []) {
        halo.material.color.setHex(hex);
        core.material.color.setHex(hex);
        halo.material.opacity = 0.95 * level;
        core.material.opacity = level;
      }
    },
  };
}

// ---------------------------------------------------------------- clock
// The clock beside the h-file, its display turned towards the board, the
// rocker bar hung on a pivot so `tilt(side)` rocks it (side = -1 or 1).
export function clockRig(scene, layers, manifest) {
  const holder = new THREE.Group();
  const frame = new THREE.Group();
  frame.rotation.x = -Math.PI / 2; // the clock's own CadQuery frame, z up
  holder.add(frame);
  const [px, py, pz] = manifest.clock_pivot_mm;
  const pivot = new THREE.Group();
  pivot.position.set(px, py, pz);
  frame.add(pivot);
  for (const [key, parent, offset] of [["horloge/boitier", frame, [0, 0, 0]], ["horloge/barre", pivot, [-px, -py, -pz]]]) {
    const { outer, inner } = layers[key];
    scene.remove(outer);
    for (const m of [...inner.children]) {
      m.position.set(...offset);
      parent.add(m);
    }
  }
  holder.position.set(320, 0, -60);
  holder.rotation.y = -Math.PI / 2 + 0.55;
  scene.add(holder);
  return {
    holder,
    tilt(side) {
      pivot.rotation.y = THREE.MathUtils.degToRad(F().clock_tilt_deg) * side;
    },
  };
}

// ---------------------------------------------------------------- opened piece
// Felt, coil and capacitor, ferrite magnet, and the shell above them, on the
// dimensions of the given class; explode(u) spreads them (1) or closes (0).
export function openedPiece(kind, white) {
  const d = F().pieces[kind];
  const g = new THREE.Group();
  const felt = new THREE.Mesh(new THREE.CylinderGeometry(d.base / 2, d.base / 2, F().felt, 48), MATERIALS.felt);
  const ring = new THREE.Shape();
  ring.absarc(0, 0, d.coil_od / 2, 0, Math.PI * 2);
  const hole = new THREE.Path();
  hole.absarc(0, 0, d.coil_id / 2, 0, Math.PI * 2, true);
  ring.holes.push(hole);
  const coilGeo = new THREE.ExtrudeGeometry(ring, { depth: F().coil_h, bevelEnabled: false, curveSegments: 48 });
  coilGeo.rotateX(-Math.PI / 2);
  const coil = new THREE.Mesh(coilGeo, MATERIALS.copper);
  const [cl, cw, ch] = F().capacitor;
  const cap = new THREE.Mesh(new THREE.BoxGeometry(cl, ch, cw), MATERIALS.ceramic);
  const magnet = new THREE.Mesh(new THREE.CylinderGeometry(d.magnet_d / 2, d.magnet_d / 2, F().magnet_h, 48), MATERIALS.ferrite);
  const shell = makePiece(kind, white);
  for (const m of [felt, coil, cap, magnet]) {
    m.castShadow = true;
    g.add(m);
  }
  g.add(shell);
  const gap = d.height * 0.45;
  const parts = { felt, coil, cap, magnet, shell };
  function explode(u) {
    felt.position.y = F().felt / 2;
    coil.position.y = F().felt + gap * u;
    cap.position.set(d.coil_od / 2 + cl / 2 + 0.6, F().felt + ch / 2 + gap * u, 0);
    magnet.position.y = F().felt + F().coil_h + F().magnet_h / 2 + 2 * gap * u;
    shell.position.y = 3 * gap * u;
  }
  explode(0);
  return { group: g, parts, explode, gap };
}

// ---------------------------------------------------------------- motion
// A piece lifted from `from`, carried and set down on `to` over [t0, t0 + dur].
export function carry(piece, from, to, t0, dur, t, top, lift) {
  const u = smooth((t - t0) / dur);
  const [x0, z0] = Array.isArray(from) ? from : squareXZ(from);
  const [x1, z1] = Array.isArray(to) ? to : squareXZ(to);
  piece.position.set(x0 + (x1 - x0) * u, top + Math.sin(Math.PI * u) * lift, z0 + (z1 - z0) * u);
}

// Shots: [start, end, camera from, camera to, target from, target to, fov?];
// the camera eases between its two positions over the shot.
export function frame(camera, shots, t) {
  const s = shots.find(([a, b]) => t >= a && t < b) || shots[shots.length - 1];
  const u = smooth((t - s[0]) / (s[1] - s[0]));
  const L = (p, q) => p.map((v, k) => v + (q[k] - v) * u);
  const fov = s[6] || 34;
  if (camera.fov !== fov) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }
  if (typeof s[2] === "function") s[2](camera, u);
  else camera.position.set(...L(s[2], s[3]));
  camera.lookAt(...L(s[4], s[5]));
  return s;
}

// Screen position (film pixels) of a scene point; the view offset is already
// in the projection matrix.
export function toScreen(camera, v) {
  const p = v.clone().project(camera);
  return { x: (p.x + 1) * 540, y: (1 - p.y) * 960 };
}
