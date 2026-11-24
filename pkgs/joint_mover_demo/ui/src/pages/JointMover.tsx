import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { GameControllerIcon, LockIcon, LockOpenIcon } from "../components/icons";
import { Badge, Banner, Button, Field, Section, ToggleGroup, cx } from "../components/ui";
import { createGamepadStore, type GamepadSnapshot, type Stick } from "../gamepad";
import styles from "../joint-mover.module.css";
import {
  DEFAULT_DEADZONE,
  STEP_DEGREES,
  deflectionToPosition,
  formatDegrees,
  initialMappings,
  parseRange,
  roundToStep,
  stickDeflection,
  type Range,
  type StickMapping,
} from "../mapping";
import { moveJoint } from "../move";
import type { AppPageProps } from "../zara";

/** At most this many sends per second, and only when a target changed. */
const SEND_HZ = 20;

const motors = [
  { name: "Motor 1", stick: "Left stick", side: "left" },
  { name: "Motor 2", stick: "Right stick", side: "right" },
] as const;

/** Last position handed to the backend per motor, `null` before the first. */
type Sent = [number | null, number | null];

const describe = (error: unknown) => (error instanceof Error ? error.message : String(error));

/** Raw stick position, the deadzone, and the axis that drives the motor. */
function StickPad({
  stick,
  axis,
  deadzone,
  label,
}: {
  stick: Stick;
  axis: "x" | "y";
  deadzone: number;
  label: string;
}) {
  const r = 44;
  return (
    <figure className={styles.figure}>
      <svg viewBox="0 0 112 112" className={styles.dial} role="img" aria-label={label}>
        <circle cx="56" cy="56" r={r} className={styles.dialFace} />
        <circle cx="56" cy="56" r={r * deadzone} className={styles.dialDeadzone} strokeDasharray="2 3" />
        <path
          d={axis === "y" ? `M56 ${56 - r}V${56 + r}` : `M${56 - r} 56H${56 + r}`}
          className={styles.dialTrack}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <circle cx={56 + stick.x * r} cy={56 + stick.y * r} r="8" className={styles.dialKnob} strokeWidth="3" />
      </svg>
      <figcaption className={cx(styles.tiny, styles.mono, styles.subtle)}>
        x {stick.x.toFixed(2)} · y {stick.y.toFixed(2)}
      </figcaption>
    </figure>
  );
}

const polar = (degrees: number, radius: number) => {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return `${(60 + radius * Math.cos(radians)).toFixed(2)} ${(60 + radius * Math.sin(radians)).toFixed(2)}`;
};

/** Target as a needle (0° up) inside the allowed range's arc. */
function TargetDial({ degrees, range, label }: { degrees: number | null; range: Range | null; label: string }) {
  const arc =
    range && range.max - range.min < 360
      ? `M${polar(range.min, 46)}A46 46 0 ${range.max - range.min > 180 ? 1 : 0} 1 ${polar(range.max, 46)}`
      : null;
  return (
    <figure className={styles.figure}>
      <svg viewBox="0 0 120 120" className={styles.dial} aria-hidden="true">
        <circle cx="60" cy="60" r="52" className={styles.dialFace} />
        {arc ? (
          <path d={arc} className={styles.dialRange} strokeWidth="8" />
        ) : (
          <circle cx="60" cy="60" r="46" className={styles.dialRange} strokeWidth="8" />
        )}
        {degrees !== null && (
          <g transform={`rotate(${degrees % 360} 60 60)`} className={styles.dialNeedle}>
            <path d="M60 60V22" strokeWidth="4" strokeLinecap="round" />
          </g>
        )}
        <circle cx="60" cy="60" r="6" className={styles.dialKnob} strokeWidth="3" />
      </svg>
      <figcaption className={styles.figureCaption}>
        <span className={styles.target} aria-label={label}>
          {degrees === null ? "—" : formatDegrees(degrees)}
        </span>
        <span className={cx(styles.tiny, styles.subtle)}>
          {range ? `Target · ${formatDegrees(range.min)} to ${formatDegrees(range.max)}` : "Target · range invalid"}
        </span>
      </figcaption>
    </figure>
  );
}

/** Which stick direction counts as positive, worded for the selected axis. */
const directions = (axis: "x" | "y") =>
  axis === "y"
    ? [
        { invert: true, label: "Up = +" },
        { invert: false, label: "Down = +" },
      ]
    : [
        { invert: false, label: "Right = +" },
        { invert: true, label: "Left = +" },
      ];

/**
 * Drives two joints from an Xbox controller through the Gamepad API, or one joint at a time by
 * hand. Every move is one `move_joint` command to this instance.
 */
export default function JointMover({ instanceId, services }: AppPageProps) {
  const id = useId();
  const [store] = useState(createGamepadStore);
  const pad: GamepadSnapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);
  const [mappings, setMappings] = useState(initialMappings);
  const [deadzoneDraft, setDeadzoneDraft] = useState(String(DEFAULT_DEADZONE));
  const [sliderTargets, setSliderTargets] = useState<[number, number]>([0, 0]);
  const [jointNames, setJointNames] = useState<[string, string]>(["", ""]);
  // Armed for one controller generation and one instance only: connecting, disconnecting or
  // swapping the controller, or switching instance, disarms without an effect and never re-arms.
  const [armedFor, setArmedFor] = useState<{ generation: number; instance: string } | null>(null);
  const [lastSent, setLastSent] = useState<Sent>([null, null]);
  const [sendTimes, setSendTimes] = useState<number[]>([]);
  const [sendCount, setSendCount] = useState(0);
  const [sendError, setSendError] = useState<string | null>(null);
  const [now, setNow] = useState(0);

  const deadzone = Number(deadzoneDraft);
  const deadzoneError =
    !deadzoneDraft.trim() || !Number.isFinite(deadzone) || deadzone < 0 || deadzone > 0.9
      ? "Enter a deadzone from 0 to 0.9."
      : null;
  const ranges = mappings.map((mapping) => parseRange(mapping));
  const validRanges = ranges.map((range) => (typeof range === "string" ? null : range));
  const sticks = [pad.left, pad.right];
  const usingController = pad.controller !== null;
  const deflections = mappings.map((mapping, motor) =>
    stickDeflection(sticks[motor]!, mapping, deadzoneError ? 0 : deadzone)
  );
  const targets = validRanges.map((range, motor) =>
    !range
      ? null
      : usingController
        ? deflectionToPosition(deflections[motor]!, range)
        : roundToStep(Math.min(range.max, Math.max(range.min, sliderTargets[motor]!)))
  );
  const armed = armedFor !== null && armedFor.generation === pad.generation && armedFor.instance === instanceId;
  const jointErrors = jointNames.map((name, motor) =>
    !name.trim()
      ? "Enter the joint this motor drives."
      : motor === 1 && name.trim() === jointNames[0].trim()
        ? "Motor 1 already drives this joint."
        : null
  );
  const settingsError =
    deadzoneError ?? ranges.find((range) => typeof range === "string") ?? jointErrors.find((error) => error);
  const sticksCentred = deflections.every((deflection) => deflection === 0);
  const armBlocker = settingsError
    ? "Fix the settings to arm."
    : usingController && !sticksCentred
      ? "Centre both sticks to arm."
      : null;

  function arm() {
    if (armBlocker) return;
    setArmedFor({ generation: pad.generation, instance: instanceId });
    setSendError(null);
  }
  const disarm = () => setArmedFor(null);

  // A toggles arming, B always disarms. Edge-triggered: holding A doesn't flicker.
  const onButton = useRef<(button: "a" | "b") => void>(() => {});
  useEffect(() => {
    onButton.current = (button) => {
      if (button === "b" || armed) disarm();
      else arm();
    };
  });
  useEffect(() => store.onButton((button) => onButton.current(button)), [store]);

  // Losing focus stops rAF polling in most browsers, so the sticks would freeze: disarm instead.
  useEffect(() => {
    const onHidden = () => {
      if (document.visibilityState === "hidden") setArmedFor(null);
    };
    const onBlur = () => setArmedFor(null);
    document.addEventListener("visibilitychange", onHidden);
    window.addEventListener("blur", onBlur);
    return () => {
      document.removeEventListener("visibilitychange", onHidden);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  // While armed, check the targets SEND_HZ times a second and send one move per joint whose target
  // changed. The first check of each arming always sends, so the joints get the current targets.
  // Nothing queues: while a joint's move is in flight its newer targets wait, and the next check
  // after it settles sends only the latest one.
  const latest = useRef({ targets, jointNames, services });
  useEffect(() => {
    latest.current = { targets, jointNames, services };
  });
  useEffect(() => {
    if (!armed) return;
    let stopped = false;
    const requested: Sent = [null, null];
    const inFlight = [false, false];
    const check = () => {
      const { targets: current, jointNames: joints, services: target } = latest.current;
      if (current[0] == null || current[1] == null) return;
      const at = performance.now();
      let sends = 0;
      current.forEach((position, motor) => {
        if (position == null || inFlight[motor] || requested[motor] === position) return;
        requested[motor] = position;
        inFlight[motor] = true;
        sends++;
        setLastSent((sent) => (motor === 0 ? [position, sent[1]] : [sent[0], position]));
        const joint = joints[motor]!.trim();
        moveJoint(target, joint, position)
          .catch((error: unknown) => {
            if (stopped) return;
            stopped = true;
            setArmedFor(null);
            setSendError(`${joint || motors[motor]!.name} to ${formatDegrees(position)}: ${describe(error)}`);
          })
          .finally(() => {
            inFlight[motor] = false;
          });
      });
      if (!sends) return;
      setSendCount((count) => count + sends);
      setSendTimes((times) => [...times.filter((time) => time > at - 1000), ...Array<number>(sends).fill(at)]);
      setNow(at);
    };
    const first = setTimeout(check, 0);
    const timer = setInterval(check, 1000 / SEND_HZ);
    return () => {
      stopped = true;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [armed, armedFor]);

  // Refresh the measured rate while armed so it falls back to zero when the sticks are still.
  useEffect(() => {
    if (!armed) return;
    const timer = setInterval(() => setNow(performance.now()), 250);
    return () => clearInterval(timer);
  }, [armed]);
  const rate = armed ? sendTimes.filter((time) => time > now - 1000).length : 0;

  // Manual move: one move_joint call per click, never while the gamepad drives the joints.
  const [manualJoint, setManualJoint] = useState("");
  const [manualPosition, setManualPosition] = useState("0");
  const [manualBusy, setManualBusy] = useState(false);
  const [manualResult, setManualResult] = useState<{ ok: boolean; text: string } | null>(null);
  const manualDegrees = Number(manualPosition);
  const manualPositionError =
    !manualPosition.trim() || !Number.isFinite(manualDegrees) ? "Enter a position in degrees." : null;
  const manualBlocker = armed ? "Disarm the gamepad to move a joint by hand." : null;

  async function sendManual() {
    const joint = manualJoint.trim();
    if (manualBlocker || manualBusy || !joint || manualPositionError) return;
    setManualBusy(true);
    setManualResult(null);
    try {
      const reply = await moveJoint(services, joint, manualDegrees);
      setManualResult({
        ok: true,
        text: `Sent ${joint} to ${formatDegrees(manualDegrees)}. The app replied ${JSON.stringify(reply)}.`,
      });
    } catch (error) {
      setManualResult({ ok: false, text: `${joint} to ${formatDegrees(manualDegrees)}: ${describe(error)}` });
    } finally {
      setManualBusy(false);
    }
  }

  function updateMapping(motor: number, change: Partial<StickMapping>) {
    setMappings(
      (current) =>
        current.map((mapping, index) => (index === motor ? { ...mapping, ...change } : mapping)) as [
          StickMapping,
          StickMapping,
        ]
    );
  }

  return (
    <section className={styles.page} aria-labelledby={`${id}-title`} data-testid="joint-mover">
      <header className={styles.pageHeader}>
        <div className={styles.stack}>
          <h1 id={`${id}-title`} className={styles.title}>
            Joint mover
          </h1>
          <p className={styles.subtle}>
            Drive two joints with an Xbox controller (the left stick moves motor 1, the right stick motor 2), or move
            one joint by hand.
          </p>
        </div>
        <Badge>Connected</Badge>
      </header>

      {sendError && <Banner variant="error" role="alert" title="Sending failed — disarmed" description={sendError} />}

      <Section
        title="Manual move"
        description="Move one joint to a position with a single move_joint call. A reply means the app accepted the move, not that the joint reached it."
      >
        <form
          className={styles.manualForm}
          aria-label="Manual move"
          onSubmit={(event) => {
            event.preventDefault();
            void sendManual();
          }}
        >
          <Field
            label="Joint name"
            inputId={`${id}-manual-joint`}
            description="As listed in the robot's bridge file, e.g. Shoulder."
            disabled={!!manualBlocker}
          >
            <input
              id={`${id}-manual-joint`}
              className={styles.input}
              value={manualJoint}
              autoComplete="off"
              spellCheck={false}
              disabled={!!manualBlocker}
              onChange={(event) => setManualJoint(event.target.value)}
            />
          </Field>
          <Field
            label="Position"
            inputId={`${id}-manual-position`}
            description="Absolute, in degrees."
            error={manualPositionError}
            unit="°"
            disabled={!!manualBlocker}
          >
            <input
              id={`${id}-manual-position`}
              className={styles.input}
              type="number"
              step="any"
              value={manualPosition}
              disabled={!!manualBlocker}
              onChange={(event) => setManualPosition(event.target.value)}
              aria-invalid={!!manualPositionError}
            />
          </Field>
          <Button
            type="submit"
            variant="primary"
            className={styles.manualSubmit}
            disabled={!!manualBlocker || manualBusy || !manualJoint.trim() || !!manualPositionError}
            loading={manualBusy}
            aria-describedby={manualBlocker ? `${id}-manual-help` : undefined}
          >
            Move
          </Button>
        </form>
        {manualBlocker && (
          <p id={`${id}-manual-help`} className={cx(styles.small, styles.subtle)}>
            {manualBlocker}
          </p>
        )}
        {manualResult &&
          (manualResult.ok ? (
            <p role="status" aria-label="Manual move result" className={cx(styles.small, styles.wrap, styles.success)}>
              {manualResult.text}
            </p>
          ) : (
            <Banner variant="error" role="alert" title="Move failed" description={manualResult.text} />
          ))}
      </Section>

      <div className={styles.columns}>
        <Section title="Controller" description="Uses the first connected gamepad with the standard mapping.">
          <div className={styles.controller}>
            <span className={styles.controllerIcon}>
              <GameControllerIcon />
            </span>
            <div className={styles.stack} role="status" aria-label="Controller status">
              {pad.controller ? (
                <>
                  <span className={cx(styles.strong, styles.wrap)}>{pad.controller.id}</span>
                  <span className={cx(styles.small, styles.subtle)}>
                    Gamepad {pad.controller.index}
                    {pad.controller.standard ? " · standard mapping" : " · non-standard mapping, axes may differ"}
                  </span>
                </>
              ) : (
                <>
                  <span className={styles.strong}>No controller</span>
                  <span className={cx(styles.small, styles.subtle)}>
                    Connect an Xbox controller and press any button. Until then, use the sliders below.
                  </span>
                </>
              )}
            </div>
          </div>
          <dl className={cx(styles.keys, styles.small)}>
            <dt>
              <kbd className={styles.kbd}>A</kbd>
            </dt>
            <dd className={styles.subtle}>Arm or disarm (sticks must be centred to arm)</dd>
            <dt>
              <kbd className={styles.kbd}>B</kbd>
            </dt>
            <dd className={styles.subtle}>Disarm</dd>
          </dl>
          <Field
            label="Deadzone"
            inputId={`${id}-deadzone`}
            description="Stick deflection ignored around the centre, from 0 to 0.9."
            error={deadzoneError}
            disabled={armed}
          >
            <input
              id={`${id}-deadzone`}
              className={styles.input}
              type="number"
              min="0"
              max="0.9"
              step="0.05"
              value={deadzoneDraft}
              disabled={armed}
              onChange={(event) => setDeadzoneDraft(event.target.value)}
              aria-invalid={!!deadzoneError}
            />
          </Field>
        </Section>

        <Section
          title="Output"
          description={`One move_joint call per joint whose target changed, at most ${SEND_HZ} times a second per joint.`}
        >
          <div className={styles.armRow}>
            <div className={styles.stack}>
              {armed ? <Badge variant="success">Armed</Badge> : <Badge variant="neutral">Disarmed</Badge>}
              <p id={`${id}-arm-help`} className={cx(styles.small, styles.subtle)}>
                {armed
                  ? "Targets follow the controls. Releasing a stick returns its motor to the middle of its range."
                  : (armBlocker ??
                    "Nothing is sent while disarmed. Arming sends the current targets at once, so centred sticks move both motors to the middle of their ranges.")}
              </p>
            </div>
            {armed ? (
              <Button variant="destructive" size="lg" icon={LockIcon} onClick={disarm}>
                Disarm
              </Button>
            ) : (
              <Button
                variant="primary"
                size="lg"
                icon={LockOpenIcon}
                disabled={!!armBlocker}
                aria-describedby={`${id}-arm-help`}
                onClick={arm}
              >
                Arm
              </Button>
            )}
          </div>
          <dl className={styles.stats}>
            <dt className={styles.subtle}>Last sent</dt>
            <dd aria-label="Last sent">
              {lastSent.every((sent) => sent === null)
                ? "—"
                : lastSent.map((sent) => (sent === null ? "—" : formatDegrees(sent))).join(" · ")}
            </dd>
            <dt className={styles.subtle}>Updates sent</dt>
            <dd>{sendCount}</dd>
            <dt className={styles.subtle}>Send rate</dt>
            <dd>
              {rate}/s <span className={styles.subtle}>· limit {SEND_HZ}/s per joint</span>
            </dd>
            <dt className={styles.subtle}>Instance</dt>
            <dd className={styles.wrap}>{instanceId}</dd>
          </dl>
        </Section>
      </div>

      <div className={styles.columns}>
        {motors.map((motor, index) => {
          const mapping = mappings[index]!;
          const range = validRanges[index] ?? null;
          const rangeError = typeof ranges[index] === "string" ? ranges[index] : null;
          return (
            <Section
              key={motor.name}
              title={`${motor.name} · ${motor.stick}`}
              description={`${mapping.axis.toUpperCase()} axis, ${directions(mapping.axis)
                .find((d) => d.invert === mapping.invert)!
                .label.toLowerCase()}.`}
            >
              <div className={styles.preview}>
                <StickPad
                  stick={sticks[index]!}
                  axis={mapping.axis}
                  deadzone={deadzoneError ? 0 : deadzone}
                  label={`${motor.stick} position`}
                />
                <TargetDial degrees={targets[index] ?? null} range={range} label={`${motor.name} target`} />
              </div>

              {!usingController && range && (
                <div className={styles.field}>
                  <label htmlFor={`${id}-manual-${index}`} className={styles.label}>
                    {motor.name} target (no controller)
                  </label>
                  <input
                    id={`${id}-manual-${index}`}
                    className={styles.slider}
                    type="range"
                    min={range.min}
                    max={range.max}
                    step={STEP_DEGREES}
                    value={targets[index] ?? 0}
                    onChange={(event) =>
                      setSliderTargets((current) =>
                        index === 0
                          ? [Number(event.target.value), current[1]]
                          : [current[0], Number(event.target.value)]
                      )
                    }
                  />
                </div>
              )}

              <div className={styles.settings}>
                <div className={styles.span2}>
                  <Field
                    label="Joint name"
                    inputId={`${id}-joint-${index}`}
                    error={jointErrors[index]}
                    disabled={armed}
                  >
                    <input
                      id={`${id}-joint-${index}`}
                      className={styles.input}
                      value={jointNames[index]}
                      placeholder={index === 0 ? "e.g. Shoulder" : "e.g. Hip"}
                      autoComplete="off"
                      spellCheck={false}
                      disabled={armed}
                      onChange={(event) =>
                        setJointNames((current) =>
                          index === 0 ? [event.target.value, current[1]] : [current[0], event.target.value]
                        )
                      }
                      aria-invalid={!!jointErrors[index]}
                    />
                  </Field>
                </div>
                <div className={styles.field}>
                  <span id={`${id}-axis-${index}`} className={styles.label}>
                    Axis
                  </span>
                  <ToggleGroup
                    labelledBy={`${id}-axis-${index}`}
                    value={mapping.axis}
                    options={[
                      { value: "y", label: "Up / down" },
                      { value: "x", label: "Left / right" },
                    ]}
                    disabled={armed}
                    onChange={(axis) => updateMapping(index, { axis, invert: axis === "y" })}
                  />
                </div>
                <div className={styles.field}>
                  <span id={`${id}-direction-${index}`} className={styles.label}>
                    Direction
                  </span>
                  <ToggleGroup
                    labelledBy={`${id}-direction-${index}`}
                    value={String(mapping.invert)}
                    options={directions(mapping.axis).map((direction) => ({
                      value: String(direction.invert),
                      label: direction.label,
                    }))}
                    disabled={armed}
                    onChange={(value) => updateMapping(index, { invert: value === "true" })}
                  />
                </div>
                {(["minDegrees", "maxDegrees"] as const).map((key) => (
                  <Field
                    key={key}
                    label={`${key === "minDegrees" ? "Minimum" : "Maximum"} angle`}
                    inputId={`${id}-${key}-${index}`}
                    error={key === "maxDegrees" ? rangeError : null}
                    unit="°"
                    disabled={armed}
                  >
                    <input
                      id={`${id}-${key}-${index}`}
                      className={styles.input}
                      type="number"
                      step="any"
                      value={mapping[key]}
                      disabled={armed}
                      onChange={(event) => updateMapping(index, { [key]: event.target.value })}
                      aria-invalid={!!rangeError}
                    />
                  </Field>
                ))}
              </div>
              <p className={cx(styles.tiny, styles.subtle)}>
                The range is a UI default, not a hardware limit: the firmware rejects a goal outside the joint's bounds.
                Settings are locked while armed.
              </p>
            </Section>
          );
        })}
      </div>
    </section>
  );
}
