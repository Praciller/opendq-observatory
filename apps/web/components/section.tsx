import type { ReactNode } from "react";

export function Section({
  title,
  description,
  action,
  children,
  className = "",
  id,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  const titleSlug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "section";
  const headingId = id ? `${id}-heading` : `section-${titleSlug}`;
  return (
    <section aria-labelledby={headingId} className={`section-card ${className}`.trim()} id={id}>
      <div className="section-heading">
        <div>
          <h2 id={headingId}>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action && <div className="section-action">{action}</div>}
      </div>
      {children}
    </section>
  );
}
