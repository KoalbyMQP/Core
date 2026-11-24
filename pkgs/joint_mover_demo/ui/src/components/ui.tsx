import type { ButtonHTMLAttributes, ComponentType, ReactNode, SVGProps } from "react";
import styles from "../joint-mover.module.css";
import { CheckIcon, InfoIcon, WarningIcon } from "./icons";

// Plain-element stand-ins for the Driver Station components the page used to be built from (Kumo's
// LayerCard, Badge, Banner, Button, InputGroup and ToggleGroup). App pages can't import the host's
// components, and the host only generates Tailwind for its own sources, so these are styled with
// the page's CSS module.

const cx = (...names: (string | false | null | undefined)[]) => names.filter(Boolean).join(" ");

/** A card with a header (title and description) above its content. */
export function Section({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className={styles.card}>
      <header className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>{title}</h2>
        <p className={styles.small}>{description}</p>
      </header>
      <div className={styles.cardBody}>{children}</div>
    </section>
  );
}

export function Badge({
  variant = "outline",
  children,
}: {
  variant?: "outline" | "success" | "neutral";
  children: ReactNode;
}) {
  return (
    <span className={cx(styles.badge, variant === "success" && styles.badgeSuccess)}>
      {variant !== "outline" && <span className={styles.badgeDot} aria-hidden="true" />}
      {children}
    </span>
  );
}

export function Banner({
  variant = "info",
  role,
  title,
  description,
}: {
  variant?: "info" | "error";
  role: "note" | "alert";
  title: string;
  description: ReactNode;
}) {
  const Icon = variant === "error" ? WarningIcon : InfoIcon;
  return (
    <div className={cx(styles.banner, variant === "error" && styles.bannerError)} role={role}>
      <Icon className={styles.bannerIcon} />
      <div className={styles.stack}>
        <strong className={styles.bannerTitle}>{title}</strong>
        <span className={cx(styles.small, styles.wrap)}>{description}</span>
      </div>
    </div>
  );
}

export function Button({
  variant = "secondary",
  size,
  icon: Icon,
  loading,
  disabled,
  children,
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "destructive";
  size?: "lg";
  icon?: ComponentType<SVGProps<SVGSVGElement>>;
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      type={type}
      className={cx(
        styles.button,
        variant === "primary" && styles.buttonPrimary,
        variant === "destructive" && styles.buttonDestructive,
        size === "lg" && styles.buttonLarge,
        className
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {loading ? (
        <span className={styles.spinner} aria-hidden="true" />
      ) : (
        Icon && <Icon className={styles.buttonIcon} />
      )}
      {children}
    </button>
  );
}

/** A labelled input with an optional unit, hint and error, like Kumo's InputGroup. */
export function Field({
  label,
  inputId,
  description,
  error,
  unit,
  disabled,
  children,
}: {
  label: ReactNode;
  /** The id of the input in `children`, so the label points at it. */
  inputId: string;
  description?: ReactNode;
  error?: string | null;
  unit?: string;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={cx(styles.field, disabled && styles.fieldDisabled)}>
      <label htmlFor={inputId} className={styles.label}>
        {label}
      </label>
      <div className={cx(styles.control, error && styles.controlInvalid)}>
        {children}
        {unit && (
          <span className={styles.unit} aria-hidden="true">
            {unit}
          </span>
        )}
      </div>
      {error && (
        <p className={cx(styles.small, styles.fieldError)}>
          <span role="alert">{error}</span>
        </p>
      )}
      {description && <p className={cx(styles.small, styles.subtle)}>{description}</p>}
    </div>
  );
}

/** A row of mutually exclusive buttons, like Kumo's single-select ToggleGroup. */
export function ToggleGroup<T extends string>({
  labelledBy,
  value,
  options,
  disabled,
  onChange,
}: {
  labelledBy: string;
  value: T;
  options: { value: T; label: string }[];
  disabled?: boolean;
  onChange: (value: T) => void;
}) {
  return (
    <div className={styles.toggleGroup} role="group" aria-labelledby={labelledBy}>
      {options.map((option) => {
        const pressed = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            className={styles.toggle}
            aria-pressed={pressed}
            disabled={disabled}
            onClick={() => {
              // Like the host's toggle group, pressing the selected option again changes nothing.
              if (!pressed) onChange(option.value);
            }}
          >
            <CheckIcon className={cx(styles.toggleCheck, pressed && styles.toggleCheckOn)} />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export { cx };
