import assert from "node:assert/strict";
import test from "node:test";

type ContractModule = typeof import("../scripts/production-ui-contract");

async function loadContract(): Promise<ContractModule> {
  try {
    return await import("../scripts/production-ui-contract");
  } catch (error) {
    assert.fail(`production UI contract module must exist: ${String(error)}`);
  }
}

test("production UI contract extracts stylesheet URLs from HTML", async () => {
  const contract = await loadContract();
  const html = '<link rel="stylesheet" href="/_next/static/app.css"><link rel="stylesheet" href="https://cdn.example.com/extra.css">';
  const urls = contract.extractStylesheetUrls(html, "https://example.com/");
  assert.deepEqual(urls, [
    "https://example.com/_next/static/app.css",
    "https://cdn.example.com/extra.css",
  ]);
});

test("production UI contract rejects a stylesheet bundle missing shell selectors", async () => {
  const contract = await loadContract();
  assert.throws(
    () => contract.assertCssContract([".sidebar{display:flex}.app-frame{margin-left:240px}"]),
    /missing required CSS selectors/i,
  );
});

test("production UI contract accepts required selectors split across CSS chunks", async () => {
  const contract = await loadContract();
  const selectors = contract.assertCssContract([
    ".sidebar{display:flex}.mobile-header{display:none}",
    ".mobile-nav{display:none}.app-frame{margin-left:240px}.section-card{border:1px solid}",
  ]);
  assert.deepEqual(selectors, [".sidebar", ".mobile-header", ".mobile-nav", ".app-frame", ".section-card"]);
});

test("production UI verification fetches HTML and all referenced CSS before passing", async () => {
  const contract = await loadContract();
  const calls: string[] = [];
  const fakeFetch = async (input: string | URL): Promise<Response> => {
    const url = input.toString();
    calls.push(url);
    if (url === "https://example.com/") {
      return new Response(
        '<div class="app-shell"><aside class="sidebar"></aside><header class="mobile-header"></header><nav class="mobile-nav"></nav><main class="section-card"></main></div><link rel="stylesheet" href="/a.css"><link rel="stylesheet" href="/b.css">',
        { status: 200 },
      );
    }
    if (url.endsWith("/a.css")) return new Response(".sidebar{}.mobile-header{}.mobile-nav{}", { status: 200 });
    if (url.endsWith("/b.css")) return new Response(".app-frame{}.section-card{}", { status: 200 });
    return new Response("not found", { status: 404 });
  };

  const result = await contract.verifyProductionUi("https://example.com", fakeFetch);
  assert.equal(result.stylesheetCount, 2);
  assert.deepEqual(result.requiredSelectors, [".sidebar", ".mobile-header", ".mobile-nav", ".app-frame", ".section-card"]);
  assert.deepEqual(calls, ["https://example.com/", "https://example.com/a.css", "https://example.com/b.css"]);
});

test("web package exposes a production UI verification command", async () => {
  const { readFile } = await import("node:fs/promises");
  const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8")) as {
    scripts?: Record<string, string>;
  };
  assert.equal(packageJson.scripts?.["verify:production-ui"], "tsx scripts/verify-production-ui.ts");
});

test("production UI verification CLI runs successfully in this package mode", async () => {
  const { createServer } = await import("node:http");
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const { resolve } = await import("node:path");
  const server = createServer((request, response) => {
    if (request.url === "/app.css") {
      response.end(".sidebar{}.mobile-header{}.mobile-nav{}.app-frame{}.section-card{}");
      return;
    }
    response.setHeader("content-type", "text/html");
    response.end('<div class="app-shell"><aside class="sidebar"></aside><header class="mobile-header"></header><nav class="mobile-nav"></nav><main class="section-card"></main></div><link rel="stylesheet" href="/app.css">');
  });
  await new Promise<void>((resolveListen) => server.listen(0, "127.0.0.1", resolveListen));
  const address = server.address();
  assert.ok(address && typeof address !== "string");
  try {
    const run = promisify(execFile);
    const cli = resolve(process.cwd(), "node_modules/tsx/dist/cli.mjs");
    const result = await run(process.execPath, [cli, "scripts/verify-production-ui.ts", `http://127.0.0.1:${address.port}`]);
    assert.match(result.stdout, /PRODUCTION_UI=PASS/);
  } finally {
    await new Promise<void>((resolveClose) => server.close(() => resolveClose()));
  }
});

test("repository exposes a manual post-deploy production UI verification workflow", async () => {
  const { readFile } = await import("node:fs/promises");
  const { resolve } = await import("node:path");
  let workflow = "";
  try {
    workflow = await readFile(resolve(process.cwd(), "../../.github/workflows/verify-production-ui.yml"), "utf8");
  } catch (error) {
    assert.fail(`post-deploy verification workflow must exist: ${String(error)}`);
  }
  assert.match(workflow, /workflow_dispatch:/);
  assert.match(workflow, /npm run verify:production-ui/);
  assert.match(workflow, /working-directory:\s*apps\/web/);
});

test("stylesheet extraction does not depend on link attribute order", async () => {
  const contract = await loadContract();
  const html = '<link href="/reordered.css" data-precedence="next" rel="stylesheet">';
  assert.deepEqual(contract.extractStylesheetUrls(html, "https://example.com/"), [
    "https://example.com/reordered.css",
  ]);
});
