import { CHART } from "../data/chart";
import { LOCATION_IDS, type LocationId } from "../data/ids";
import { LOCATIONS } from "../data/locations";

// Draws the journal's sea chart (src/data/chart.ts) as one SVG: sea, shoals
// and land, the drowned town showing through, soundings and routes, the beam
// sweeping its reach, fog over everything past it, the lights that went out
// waiting in the fog, and a compass rose.

type Pt = readonly [number, number];

export interface ChartView {
  stage: number;
  here: LocationId;
  /** Inside the beam's reach: drawn and named. */
  revealed: (l: LocationId) => boolean;
  /** You could set out for it now. */
  open: (l: LocationId) => boolean;
  beaconLit: boolean;
}

const f = (p: Pt) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

/** A smooth curve through a polyline's midpoints; closed, an outline. */
function smooth(pts: readonly Pt[], closed: boolean): string {
  const n = pts.length;
  if (!closed) {
    let d = `M${f(pts[0]!)}`;
    for (let i = 1; i < n - 1; i++) d += `Q${f(pts[i]!)} ${f(mid(pts[i]!, pts[i + 1]!))}`;
    return `${d}L${f(pts[n - 1]!)}`;
  }
  let d = `M${f(mid(pts[0]!, pts[1]!))}`;
  for (let i = 1; i <= n; i++) {
    const p = pts[i % n]!;
    d += `Q${f(p)} ${f(mid(p, pts[(i + 1) % n]!))}`;
  }
  return `${d}Z`;
}

function lighthouse(x: number, y: number, cls: string): string {
  return `<g class="${cls}" transform="translate(${x} ${y})"><path d="M-3.2 7L-2 -3H2L3.2 7Z"/><rect x="-2.4" y="-6.2" width="4.8" height="3.2"/><path d="M-3 -6.2L0 -9L3 -6.2Z"/></g>`;
}

function wreck(x: number, y: number): string {
  return `<g class="ship" transform="translate(${x} ${y}) rotate(-18)"><path d="M-8 -1Q-6 4 0 4Q6 4 9 -1Z"/><path class="spar" d="M-2 -1V-9M3 -1V-6.5M-2 -7L3 -5"/></g>`;
}

function rose([cx, cy]: Pt, r: number): string {
  const point = (k: number) => {
    const a = (k * Math.PI) / 4 - Math.PI / 2;
    const long = k % 2 === 0;
    const R = long ? r : r * 0.55;
    const w = (long ? 0.17 : 0.13) * r;
    const tip: Pt = [cx + Math.cos(a) * R, cy + Math.sin(a) * R];
    const left: Pt = [cx + Math.cos(a - Math.PI / 2) * w, cy + Math.sin(a - Math.PI / 2) * w];
    const right: Pt = [cx + Math.cos(a + Math.PI / 2) * w, cy + Math.sin(a + Math.PI / 2) * w];
    return `<path class="face" d="M${cx} ${cy}L${f(tip)}L${f(left)}Z"/><path class="shade" d="M${cx} ${cy}L${f(tip)}L${f(right)}Z"/>`;
  };
  const diagonals = [1, 3, 5, 7].map(point).join("");
  const cardinals = [0, 2, 4, 6].map(point).join("");
  return `<g class="rose"><circle cx="${cx}" cy="${cy}" r="${r * 0.72}"/>${diagonals}${cardinals}<text x="${cx}" y="${cy - r - 4}">N</text></g>`;
}

export function chartSvg(v: ChartView): string {
  const C = CHART;
  const [W, H] = C.size;
  const home = C.at.home;
  const [hx, hy] = home;
  const reach = C.reach[Math.min(v.stage, C.reach.length - 1)]!;

  const rhumbs = Array.from({ length: 16 }, (_, k) => {
    const a = (k * Math.PI) / 8;
    return `M${C.rose[0]} ${C.rose[1]}l${(Math.cos(a) * 700).toFixed(0)} ${(Math.sin(a) * 700).toFixed(0)}`;
  }).join("");
  const main = `${smooth(C.coast, false)}L-12 ${H + 12}L-12 -12Z`;
  const isles = C.islands.map((o) => smooth(o, true)).join("");

  // The drowned town: a street grid turned off true, roofs along it, the church.
  const D = C.drowned;
  const [c, s] = [Math.cos(D.turn), Math.sin(D.turn)];
  const town = (p: Pt): Pt => [D.origin[0] + p[0] * c - p[1] * s, D.origin[1] + p[0] * s + p[1] * c];
  const deg = ((D.turn * 180) / Math.PI).toFixed(1);
  const streets = D.streets.map(([a, b]) => `M${f(town(a!))}L${f(town(b!))}`).join("");
  const roofs = D.roofs
    .map((p) => {
      const [x, y] = town(p);
      return `<rect x="${(x - 2.6).toFixed(1)}" y="${(y - 1.8).toFixed(1)}" width="5.2" height="3.6" transform="rotate(${deg} ${x.toFixed(1)} ${y.toFixed(1)})"/>`;
    })
    .join("");
  const [sx, sy] = town(D.spire);
  const drowned = `<g class="drowned"><path d="${streets}"/>${roofs}<path d="M${f([sx, sy - 5])}V${(sy + 3).toFixed(1)}M${f([sx - 2.5, sy - 2.5])}H${(sx + 2.5).toFixed(1)}"/>
    <path d="${smooth(C.poles, false)}"/>${C.poles.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1"/>`).join("")}</g>`;

  const rocks = C.rocks.map(([x, y]) => `M${x - 2} ${y}h4M${x} ${y - 2}v4`).join("");
  const soundings = C.soundings.map(([x, y, t]) => `<text x="${x}" y="${y}">${t}</text>`).join("");

  // Routes: the cliff path on foot, the boat from the dock below the Rest.
  const dock: Pt = [hx + 4, hy + 10];
  const routes = LOCATION_IDS.filter((l) => l !== "home" && v.revealed(l))
    .map((l) => {
      const ctrl = C.routes[l];
      if (!ctrl) return "";
      return `<path class="route${v.open(l) ? "" : " closed"}" d="M${f(dock)}Q${f(ctrl)} ${f(C.at[l])}"/>`;
    })
    .join("");
  const foot = `<path class="route foot" d="${smooth(C.cliffPath, false)}"/>`;

  // The beam: a wedge turning round the Rest, its reach lit, fog past it.
  const a = 0.13;
  const beam = `<g class="beam" style="transform-origin:${hx}px ${hy}px"><path fill="url(#ch-beam)" d="M${hx} ${hy}L${f([hx + Math.cos(-a) * reach, hy + Math.sin(-a) * reach])}A${reach} ${reach} 0 0 1 ${f([hx + Math.cos(a) * reach, hy + Math.sin(a) * reach])}Z"/></g>`;
  const fogFrom = ((reach - 28) / (reach + 22)).toFixed(3);

  const marks = LOCATION_IDS.map((l) => {
    const [x, y] = C.at[l];
    const d = LOCATIONS[l];
    if (!v.revealed(l)) return `<text class="label unknown" x="${x}" y="${y + 4}">?</text>`;
    const here = l === v.here ? `<circle class="here" cx="${x}" cy="${y}" r="7"/>` : "";
    let mark = `<circle class="place" cx="${x}" cy="${y}" r="3.6"/>`;
    let label = `<text class="label" x="${x}" y="${y + 18}">${d.name}</text>`;
    if (l === "home") {
      mark = `<circle class="glow" cx="${x}" cy="${y}" r="10"/>${lighthouse(x, y, "light lit")}`;
      label = `<text class="label home" x="${x - 4}" y="${y + 24}">${d.name}</text>`;
    } else if (l === "beacon") {
      mark = `${v.beaconLit ? `<circle class="glow" cx="${x}" cy="${y}" r="10"/>` : ""}${lighthouse(x, y, v.beaconLit ? "light lit" : "light")}`;
      label = `<text class="label" x="${x}" y="${y + 26}">${d.name}</text>`;
    } else if (l === "wreck") {
      mark = wreck(x, y - 2);
    } else if (l === "shore") {
      label = `<text class="label" x="${x - 8}" y="${y - 8}" text-anchor="end">${d.name}</text>`;
    }
    return here + mark + label;
  }).join("");
  const dead = C.deadLights.map(([x, y]) => `${lighthouse(x, y, "light dead")}<text class="tiny" x="${x}" y="${y + 16}">dark</text>`).join("");

  return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Sea chart: Lantern's Rest and the coast its beam can reach">
    <defs>
      <linearGradient id="ch-sea" x1="0" x2="1" y1="0" y2="0.3"><stop offset="0" stop-color="#0e3247"/><stop offset="1" stop-color="#071b28"/></linearGradient>
      <radialGradient id="ch-lit" gradientUnits="userSpaceOnUse" cx="${hx}" cy="${hy}" r="${reach}"><stop offset="0" stop-color="#ffe7b0" stop-opacity="0.2"/><stop offset="1" stop-color="#ffe7b0" stop-opacity="0"/></radialGradient>
      <linearGradient id="ch-beam" gradientUnits="userSpaceOnUse" x1="${hx}" y1="${hy}" x2="${hx + reach}" y2="${hy}"><stop offset="0" stop-color="#ffe7b0" stop-opacity="0.32"/><stop offset="1" stop-color="#ffe7b0" stop-opacity="0"/></linearGradient>
      <radialGradient id="ch-reach-g" gradientUnits="userSpaceOnUse" cx="${hx}" cy="${hy}" r="${reach + 22}"><stop offset="${fogFrom}" stop-color="#000"/><stop offset="1" stop-color="#fff"/></radialGradient>
      <mask id="ch-reach"><rect width="${W}" height="${H}" fill="url(#ch-reach-g)"/></mask>
      <filter id="ch-fog" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.011 0.026" numOctaves="3" seed="4"/><feColorMatrix values="0 0 0 0 0.6  0 0 0 0 0.66  0 0 0 0 0.7  0 0 0 0.7 0.1"/></filter>
    </defs>
    <rect width="${W}" height="${H}" fill="url(#ch-sea)"/>
    <path class="rhumb" d="${rhumbs}"/>
    ${drowned}
    <path class="shoal-edge" d="${main}"/><path class="shoal" d="${main}"/><path class="shallows" d="${main}"/>
    <g class="small"><path class="shoal-edge" d="${isles}"/><path class="shoal" d="${isles}"/><path class="shallows" d="${isles}"/></g>
    <path class="land" d="${main}${isles}"/><path class="coast" d="${main}${isles}"/>
    <path class="sandbar" d="${smooth(C.sandbar, false)}"/>
    <path class="rocks" d="${rocks}"/>
    <g class="sound">${soundings}</g>
    ${foot}${routes}
    <circle cx="${hx}" cy="${hy}" r="${reach}" fill="url(#ch-lit)"/>
    ${beam}
    <g mask="url(#ch-reach)"><rect class="fog" width="${W}" height="${H}"/><rect width="${W}" height="${H}" filter="url(#ch-fog)"/></g>
    ${dead}${marks}
    <text class="title" x="12" y="22">The Drowned Coast</text>
    <text class="subtitle" x="12" y="35">Lantern's Rest and the lights beyond</text>
    <g class="scale"><path d="M122 256h40M122 253v6M142 254v4M162 253v6"/><text x="142" y="266">one league</text></g>
    ${rose(C.rose, 20)}
  </svg>`;
}
