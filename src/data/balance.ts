/** Player and economy tuning. Change numbers here, not in systems. */
export const BALANCE = {
  player: {
    baseHp: 100,
    hpPerCombatLevel: 5,
    eyeHeight: 1.65,
    radius: 0.35,
    walkSpeed: 5.2,
    accel: 60,
    airControl: 0.35,
    gravity: 24,
    jumpSpeed: 7.2,
    wadeSpeedMul: 0.6,
    swimSpeedMul: 0.45,
    dash: { distance: 6, duration: 0.18, iframes: 0.28, cooldown: 1.2 },
    eatSeconds: 0.6,
  },
  /** The Keeper's Lantern Flare (Q): a cone of light that knocks enemies off their stride. */
  flare: {
    cooldown: 9,
    range: 15,
    /** Half-angle of the cone, degrees. Generous: it's a panic button, not a sniper shot. */
    coneDeg: 42,
    /** Gloom pockets this close burn away whichever way you face. */
    gloomRadius: 4,
    /** Seconds the light stays blinding (the stagger length per enemy is in enemies.ts). */
    flash: 0.5,
  },
  /** Gloom pockets: patches of the sea's darkness that shroud loot until a Flare burns them off. */
  gloom: {
    /** Seconds inside before the chill starts to bite. */
    grace: 1.2,
    drainPerSecond: 4,
    /** The Gloom wears you down but never kills: it stops draining at this much health. */
    floorHp: 15,
  },
  inventory: {
    baseSlots: 12,
    /** Fraction of each unbanked common stack lost on defeat (rounded down). */
    deathLoss: 0.4,
  },
  save: {
    autosaveSecondsAtHome: 60,
  },
} as const;
