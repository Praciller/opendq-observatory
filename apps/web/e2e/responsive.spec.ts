import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", title: "Operational overview" },
  { path: "/quality", title: "Quality evidence" },
  { path: "/drift", title: "Drift signals" },
  { path: "/incidents", title: "Incidents" },
  { path: "/lineage", title: "Operational lineage" },
  { path: "/reliability", title: "Reliability evidence" },
] as const;

const viewports = [
  { name: "small mobile", width: 360, height: 780, mobileNavigation: true },
  { name: "mobile", width: 390, height: 844, mobileNavigation: true },
  { name: "tablet", width: 768, height: 1024, mobileNavigation: true },
  { name: "desktop", width: 1440, height: 900, mobileNavigation: false },
] as const;

for (const viewport of viewports) {
  test(`${viewport.name} routes render, navigate, and avoid page overflow`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const route of routes) {
      const response = await page.goto(route.path, { waitUntil: "domcontentloaded" });
      expect(response?.status(), `${viewport.name}: ${route.path} HTTP`).toBe(200);
      await expect(page.locator("main#main-content")).toBeVisible();
      await expect(page.getByRole("heading", { name: route.title, level: 1 })).toBeVisible();
      await expect(page.locator(".section-card").first()).toBeVisible();

      const desktopNav = page.locator(".sidebar-nav");
      const mobileNav = page.locator(".mobile-nav");
      if (viewport.mobileNavigation) {
        await expect(page.locator(".sidebar")).toBeHidden();
        await expect(page.locator(".mobile-header")).toBeVisible();
        await expect(mobileNav).toBeVisible();
      } else {
        await expect(page.locator(".sidebar")).toBeVisible();
        await expect(page.locator(".mobile-header")).toBeHidden();
        await expect(mobileNav).toBeHidden();
      }

      const nav = viewport.mobileNavigation ? mobileNav : desktopNav;
      await expect(nav.locator(`a[href="${route.path}"]`)).toHaveAttribute(
        "aria-current",
        "page",
      );

      await page.evaluate(() => document.fonts.ready);
      const { scrollWidth, clientWidth } = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(
        scrollWidth,
        `${viewport.name} ${route.path}: page horizontal overflow`,
      ).toBeLessThanOrEqual(clientWidth + 1);
    }
  });
}

test("keyboard skip navigation reaches the main landmark", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main-content$/);
});

test("desktop primary navigation changes the route", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.locator(".sidebar-nav").getByRole("link", { name: "Quality" }).click();
  await expect(page).toHaveURL(/\/quality$/);
  await expect(page.getByRole("heading", { name: "Quality evidence", level: 1 })).toBeVisible();
});
