/**
 * Polls the Gamepad API once per animation frame and exposes the first connected controller as an
 * external store for `useSyncExternalStore`.
 *
 * `navigator.getGamepads()` is the only source of truth, so `gamepadconnected`/`gamepaddisconnected`
 * aren't needed: polling sees a controller once the browser exposes it (after its first button
 * press, in Chromium) and sees it vanish when it disconnects. Axes use the "standard" mapping (Xbox controllers in Chromium and Firefox):
 * axes 0/1 = left stick X/Y, 2/3 = right stick X/Y, with Y = −1 when the stick is pushed up.
 */

export type Stick = { x: number; y: number };

export type GamepadSnapshot = {
  /** Bumped whenever the active controller changes (connects, disconnects, or is replaced). */
  generation: number;
  controller: { index: number; id: string; standard: boolean } | null;
  left: Stick;
  right: Stick;
};

/** Controller buttons the page reacts to, as rising edges (press, not hold). */
export type GamepadButton = "a" | "b";

// Standard-mapping button indices.
const BUTTONS: Record<GamepadButton, number> = { a: 0, b: 1 };
// Axes are rounded so tiny jitter doesn't re-render the page every frame.
const AXIS_RESOLUTION = 100;

const centred: Stick = { x: 0, y: 0 };
export const disconnected: GamepadSnapshot = { generation: 0, controller: null, left: centred, right: centred };

const round = (value: number | undefined) => Math.round((value ?? 0) * AXIS_RESOLUTION) / AXIS_RESOLUTION + 0;
const sameStick = (a: Stick, b: Stick) => a.x === b.x && a.y === b.y;

function firstGamepad() {
  const pads = typeof navigator.getGamepads === "function" ? Array.from(navigator.getGamepads()) : [];
  const connected = pads.filter((pad): pad is Gamepad => !!pad && pad.connected);
  return connected.find((pad) => pad.mapping === "standard") ?? connected[0] ?? null;
}

export function createGamepadStore() {
  let snapshot = disconnected;
  let frame = 0;
  let pressed: Record<GamepadButton, boolean> = { a: false, b: false };
  const listeners = new Set<() => void>();
  const buttonListeners = new Set<(button: GamepadButton) => void>();

  function poll() {
    const pad = firstGamepad();
    const next: Omit<GamepadSnapshot, "generation"> = pad
      ? {
          controller: { index: pad.index, id: pad.id, standard: pad.mapping === "standard" },
          left: { x: round(pad.axes[0]), y: round(pad.axes[1]) },
          right: { x: round(pad.axes[2]), y: round(pad.axes[3]) },
        }
      : disconnected;

    const nowPressed = { a: !!pad?.buttons[BUTTONS.a]?.pressed, b: !!pad?.buttons[BUTTONS.b]?.pressed };
    // A different controller (or none) must not inherit the old one's held buttons as a new press.
    const sameController =
      next.controller?.index === snapshot.controller?.index && next.controller?.id === snapshot.controller?.id;
    const edges = sameController
      ? (Object.keys(BUTTONS) as GamepadButton[]).filter((button) => nowPressed[button] && !pressed[button])
      : [];
    pressed = nowPressed;

    const changed =
      !sameController ||
      next.controller?.standard !== snapshot.controller?.standard ||
      !sameStick(next.left, snapshot.left) ||
      !sameStick(next.right, snapshot.right);
    if (changed) {
      snapshot = { ...next, generation: snapshot.generation + (sameController ? 0 : 1) };
      listeners.forEach((listener) => listener());
    }
    for (const button of edges) buttonListeners.forEach((listener) => listener(button));
    frame = requestAnimationFrame(poll);
  }

  function track<T>(set: Set<T>, listener: T) {
    set.add(listener);
    if (!frame) frame = requestAnimationFrame(poll);
    return () => {
      set.delete(listener);
      if (listeners.size + buttonListeners.size === 0) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    };
  }

  return {
    subscribe: (listener: () => void) => track(listeners, listener),
    /** Called once per press of A or B on the active controller. */
    onButton: (listener: (button: GamepadButton) => void) => track(buttonListeners, listener),
    getSnapshot: () => snapshot,
    getServerSnapshot: () => disconnected,
  };
}

export type GamepadStore = ReturnType<typeof createGamepadStore>;
