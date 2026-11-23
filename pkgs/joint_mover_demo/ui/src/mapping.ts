/** How one stick drives one motor. Local UI settings, not a backend payload. */
export type StickMapping = {
  axis: "x" | "y";
  /** Flip the axis. The Gamepad API reports stick-up as −1, so Y is inverted by default: up = positive. */
  invert: boolean;
  minDegrees: string;
  maxDegrees: string;
};

export type Range = { min: number; max: number };

/** Output resolution. Positions are rounded to this step, so stick noise doesn't trigger sends. */
export const STEP_DEGREES = 0.5;
export const DEFAULT_DEADZONE = 0.15;

/**
 * ±45° is a UI default, not a hardware limit. It matches the narrowest joint in Core's sample
 * crab_api bridge.toml (Shoulder, Bounds = [-45, 45]); real limits must come from the backend.
 */
export const initialMappings: [StickMapping, StickMapping] = [
  { axis: "y", invert: true, minDegrees: "-45", maxDegrees: "45" },
  { axis: "y", invert: true, minDegrees: "-45", maxDegrees: "45" },
];

export function parseRange(mapping: StickMapping): Range | string {
  const min = Number(mapping.minDegrees);
  const max = Number(mapping.maxDegrees);
  if (!mapping.minDegrees.trim() || !mapping.maxDegrees.trim() || !Number.isFinite(min) || !Number.isFinite(max))
    return "Enter finite minimum and maximum angles.";
  if (min >= max) return "The minimum must be less than the maximum.";
  return { min, max };
}

/** Zero inside the deadzone, then rescaled so the output still reaches ±1 at full deflection. */
export function applyDeadzone(value: number, deadzone: number) {
  const magnitude = Math.abs(value);
  if (magnitude <= deadzone) return 0;
  return Math.sign(value) * Math.min(1, (magnitude - deadzone) / (1 - deadzone));
}

/** Stick deflection −1…1 to an absolute position: centred stick = middle of the range. */
export function deflectionToPosition(deflection: number, range: Range) {
  const middle = (range.min + range.max) / 2;
  const position = middle + (deflection * (range.max - range.min)) / 2;
  return roundToStep(Math.min(range.max, Math.max(range.min, position)));
}

export function roundToStep(degrees: number) {
  // `+ 0` turns −0 into 0 so a centred stick reads "0°", not "-0°".
  return Math.round(degrees / STEP_DEGREES) * STEP_DEGREES + 0;
}

export function stickDeflection(stick: { x: number; y: number }, mapping: StickMapping, deadzone: number) {
  const raw = applyDeadzone(stick[mapping.axis], deadzone);
  return mapping.invert ? -raw + 0 : raw;
}

export function formatDegrees(degrees: number) {
  return `${degrees.toFixed(1)}°`;
}
