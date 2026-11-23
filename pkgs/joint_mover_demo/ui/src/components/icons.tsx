import type { SVGProps } from "react";

// Inline icons in the style of the Driver Station's (Phosphor): the page can't use the host's icon
// library, and these few don't need one of their own.

type IconProps = SVGProps<SVGSVGElement>;

const base = {
  viewBox: "0 0 24 24",
  width: "1em",
  height: "1em",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

export const CheckIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);

export const InfoIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5M12 7.5v.01" />
  </svg>
);

export const WarningIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M10.3 4.2L2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z" />
    <path d="M12 9.5v4M12 17v.01" />
  </svg>
);

export const GameControllerIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M7.5 6.5h9a5 5 0 0 1 4.9 4l1 5.2a2.6 2.6 0 0 1-4.6 2.1L15.5 15h-7l-2.3 2.8a2.6 2.6 0 0 1-4.6-2.1l1-5.2a5 5 0 0 1 4.9-4z" />
    <path d="M8 9.5v3M6.5 11h3M15 10.5v.01M17 12v.01" />
  </svg>
);

export const LockIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <rect x="4.5" y="10.5" width="15" height="10" rx="1.5" />
    <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
  </svg>
);

export const LockOpenIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <rect x="4.5" y="10.5" width="15" height="10" rx="1.5" />
    <path d="M8 10.5V7a4 4 0 0 1 7.7-1.5" />
  </svg>
);
