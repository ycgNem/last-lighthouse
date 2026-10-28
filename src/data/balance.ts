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
  inventory: {
    baseSlots: 12,
    /** Fraction of each unbanked common stack lost on defeat (rounded down). */
    deathLoss: 0.4,
  },
  save: {
    autosaveSecondsAtHome: 60,
  },
} as const;
