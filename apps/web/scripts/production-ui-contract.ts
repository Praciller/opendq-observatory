export function extractStylesheetUrls(html: string, baseUrl: string): string[] {
  const urls: string[] = [];
  for (const tag of html.match(/<link\b[^>]*>/gi) ?? []) {
    const rel = tag.match(/\brel=["']([^"']+)["']/i)?.[1] ?? "";
    if (!rel.split(/\s+/).includes("stylesheet")) continue;
    const href = tag.match(/\bhref=["']([^"']+)["']/i)?.[1];
    if (href) urls.push(new URL(href, baseUrl).toString());
  }
  return urls;
}

export const REQUIRED_CSS_SELECTORS = [
  ".sidebar",
  ".mobile-header",
  ".mobile-nav",
  ".app-frame",
  ".section-card",
] as const;

export function assertCssContract(stylesheets: string[]): string[] {
  const combined = stylesheets.join("\n");
  const missing = REQUIRED_CSS_SELECTORS.filter((selector) => !combined.includes(selector));
  if (missing.length > 0) {
    throw new Error(`Missing required CSS selectors: ${missing.join(", ")}`);
  }
  return [...REQUIRED_CSS_SELECTORS];
}

const REQUIRED_MARKUP_CLASSES = ["app-shell", "sidebar", "mobile-header", "mobile-nav", "section-card"] as const;

type FetchLike = (input: string | URL, init?: RequestInit) => Promise<Response>;

export interface ProductionUiVerification {
  baseUrl: string;
  stylesheetCount: number;
  requiredSelectors: string[];
}

function assertOk(response: Response, label: string): void {
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
}

export function assertShellMarkup(html: string): void {
  const missing = REQUIRED_MARKUP_CLASSES.filter((name) => !html.includes(`class=\"${name}`) && !html.includes(` ${name}`));
  if (missing.length > 0) throw new Error(`Missing required shell markup: ${missing.join(", ")}`);
}

export async function verifyProductionUi(baseUrl: string, fetcher: FetchLike = fetch): Promise<ProductionUiVerification> {
  const rootUrl = new URL("/", baseUrl).toString();
  const root = await fetcher(rootUrl, { redirect: "follow" });
  assertOk(root, "Production root");
  const html = await root.text();
  assertShellMarkup(html);
  const stylesheetUrls = extractStylesheetUrls(html, rootUrl);
  if (stylesheetUrls.length === 0) throw new Error("Production HTML references no stylesheets");
  const stylesheets: string[] = [];
  for (const stylesheetUrl of stylesheetUrls) {
    const response = await fetcher(stylesheetUrl, { redirect: "follow" });
    assertOk(response, `Stylesheet ${stylesheetUrl}`);
    stylesheets.push(await response.text());
  }

  return {
    baseUrl: rootUrl,
    stylesheetCount: stylesheetUrls.length,
    requiredSelectors: assertCssContract(stylesheets),
  };
}
