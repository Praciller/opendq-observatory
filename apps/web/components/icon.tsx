import type { SVGProps } from "react";

export type IconName =
  | "activity"
  | "arrow-right"
  | "check"
  | "chevron-down"
  | "database"
  | "grid"
  | "info"
  | "link"
  | "list"
  | "pulse"
  | "shield"
  | "spark"
  | "warning"
  | "x";

const paths: Record<IconName, React.ReactNode> = {
  activity: <><path d="M3 12h4l2.2-7 4.2 14L16 9l2 3h3" /><circle cx="3" cy="12" r="1" fill="currentColor" stroke="none" /></>,
  "arrow-right": <><path d="M4 12h15" /><path d="m14 6 6 6-6 6" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  "chevron-down": <path d="m6 9 6 6 6-6" />,
  database: <><ellipse cx="12" cy="5" rx="7" ry="3" /><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5" /><path d="M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7" /></>,
  grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
  info: <><circle cx="12" cy="12" r="8" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  link: <><path d="m10 13 4-4" /><path d="M7.5 17.5 6 19a3.5 3.5 0 0 1-5-5l3.5-3.5a3.5 3.5 0 0 1 5 0" /><path d="m16.5 6.5 1.5-1.5a3.5 3.5 0 0 1 5 5L19.5 13.5a3.5 3.5 0 0 1-5 0" /></>,
  list: <><path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path d="M3 12h.01" /><path d="M3 18h.01" /></>,
  pulse: <><path d="M3 12h3l2-5 4 10 2-5h7" /><path d="M3 5v14" /></>,
  shield: <path d="M12 3 19 6v5c0 4.7-2.8 8.1-7 10-4.2-1.9-7-5.3-7-10V6l7-3Z" />,
  spark: <><path d="m12 3 1.2 5.8L19 10l-5.8 1.2L12 17l-1.2-5.8L5 10l5.8-1.2L12 3Z" /><path d="m19 16 .5 2.5L22 19l-2.5.5L19 22l-.5-2.5L16 19l2.5-.5L19 16Z" /></>,
  warning: <><path d="m12 4 9 16H3L12 4Z" /><path d="M12 9v5" /><path d="M12 17h.01" /></>,
  x: <><path d="m6 6 12 12" /><path d="m18 6-12 12" /></>,
};

export function Icon({ name, size = 18, ...props }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg aria-hidden="true" fill="none" height={size} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" width={size} {...props}>
      {paths[name]}
    </svg>
  );
}
