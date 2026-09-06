import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

function order(text: string, labels: string[]): boolean {
  let previous = -1;
  for (const label of labels) {
    const current = text.indexOf(label);
    if (current < 0 || current <= previous) return false;
    previous = current;
  }
  return true;
}

test("the shared shell exposes the six read-only navigation paths and skip link", () => {
  const shell = source("components/app-shell.tsx");
  for (const path of ["/", "/quality", "/drift", "/incidents", "/lineage", "/reliability"]) {
    assert.match(shell, new RegExp(`href: \"${path.replace("/", "\\/")}\"`));
  }
  assert.match(shell, /href="#main-content"/);
  assert.match(shell, /aria-current={active \? "page" : undefined}/);
  assert.match(shell, /Read-only console/);
});

test("the overview keeps operational priority before dataset health and investigation links", () => {
  const overview = source("app/page.tsx");
  assert.equal(order(overview, ["Platform state", "Needs attention", "Dataset health", "Investigate next"]), true);
  assert.doesNotMatch(overview, /Phase\s+\d/i);
  assert.match(overview, /Active incidents/);
  assert.match(overview, /Drift signals/);
});

test("incident detail keeps deterministic evidence ahead of lifecycle and optional AI", () => {
  const detail = source("app/incidents/[id]/page.tsx");
  assert.equal(order(detail, ["title=\"Incident summary\"", "title=\"Deterministic root cause\"", "title=\"Evidence\"", "title=\"Blast radius\"", "title=\"Lifecycle\"", "title=\"AI Incident Copilot\""]), true);
  assert.match(detail, /<EvidenceList record={incident\.evidence} \/>/);
  assert.match(detail, /<RawEvidence value={incident\.evidence} \/>/);
});

test("lineage surfaces the shared staged flow on both index and dataset routes", () => {
  const lineage = source("app/lineage/page.tsx");
  const datasetLineage = source("app/lineage/[dataset]/page.tsx");
  assert.match(lineage, /<LineageFlow nodes={data\.nodes} \/>/);
  assert.match(datasetLineage, /<LineageFlow nodes={data\.nodes} \/>/);
  assert.match(source("components/lineage-flow.tsx"), /Dependency flow from source to dashboard/);
});

test("production route copy contains no development phase labels", () => {
  const routeFiles = [
    "app/page.tsx",
    "app/quality/page.tsx",
    "app/drift/page.tsx",
    "app/incidents/page.tsx",
    "app/incidents/[id]/page.tsx",
    "app/lineage/page.tsx",
    "app/lineage/[dataset]/page.tsx",
    "app/reliability/page.tsx",
  ];
  for (const route of routeFiles) assert.doesNotMatch(source(route), /Phase\s+\d/i, route);
  assert.match(source("app/globals.css"), /--canvas:\s+#0b1117/);
  assert.match(source("app/globals.css"), /prefers-reduced-motion/);
});
