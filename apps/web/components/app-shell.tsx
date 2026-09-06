"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "./icon";

const navigation: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/", label: "Overview", icon: "grid" },
  { href: "/quality", label: "Quality", icon: "shield" },
  { href: "/drift", label: "Drift", icon: "activity" },
  { href: "/incidents", label: "Incidents", icon: "warning" },
  { href: "/lineage", label: "Lineage", icon: "link" },
  { href: "/reliability", label: "Reliability", icon: "pulse" },
];

function isCurrentPath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Brand() {
  return (
    <Link className="brand" href="/" aria-label="OpenDQ Observatory overview">
      <span className="brand-mark"><Icon name="activity" size={20} /></span>
      <span><strong>OpenDQ</strong><small>Observatory</small></span>
    </Link>
  );
}

function Navigation({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary navigation" className={mobile ? "mobile-nav" : "sidebar-nav"}>
      {navigation.map((item) => {
        const active = isCurrentPath(pathname, item.href);
        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={`nav-link${active ? " is-active" : ""}`}
            href={item.href}
            key={item.href}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="sidebar">
        <Brand />
        <div className="sidebar-divider" />
        <p className="nav-label">Workspace</p>
        <Navigation />
        <div className="sidebar-footer">
          <span className="read-only-mark"><span aria-hidden="true" />Read-only console</span>
          <span>Persisted evidence only</span>
        </div>
      </aside>
      <div className="app-frame">
        <header className="mobile-header">
          <Brand />
          <span className="read-only-mark"><span aria-hidden="true" />Read-only</span>
        </header>
        <Navigation mobile />
        <div className="content-wrap">{children}</div>
        <footer className="app-footer">Read-only console · persisted evidence only</footer>
      </div>
    </div>
  );
}
