import assert from "node:assert/strict";
import test from "node:test";
import { setTimeout as delay } from "node:timers/promises";
import postgres from "postgres";

const fixture = process.env.OPENDQ_TEST_DATABASE_URL;
assert.ok(fixture, "Set OPENDQ_TEST_DATABASE_URL to the disposable PostgreSQL 16 fixture");
const target = new URL(fixture);
assert.equal(target.hostname, "127.0.0.1");
assert.equal(target.pathname, "/opendq_pr33_fixture");
process.env.DATABASE_URL = fixture;

const marker = "/* opendq-deadline-test */";

test("PostgreSQL deadlines abort blocked reads and recycle both pool slots", { timeout: 25_000 }, async () => {
  const { DATABASE_READ_DEADLINE_MS, getPool, query, queryValues } = await import("../lib/db");
  const { getQualitySummaries } = await import("../lib/quality");
  const { buildHealthResponse } = await import("../lib/status");
  const control = postgres(fixture, { max: 2, connect_timeout: 2 });
  const locked = await control.reserve();
  try {
    const [server] = await control`SELECT current_setting('server_version_num')::int AS version`;
    assert.equal(Math.floor(server.version / 10_000), 16);
    await locked`BEGIN`;
    await locked`LOCK TABLE datasets IN ACCESS EXCLUSIVE MODE`;

    const blocked = () => queryValues(
      `SELECT count(*) FROM datasets WHERE id > $1 ${marker}`,
      [0],
    );
    const countWaiting = async () => {
      const [row] = await control`SELECT count(*)::int AS count FROM pg_stat_activity
        WHERE datname = current_database() AND wait_event_type = 'Lock' AND query LIKE ${"%" + marker + "%"}`;
      return row.count as number;
    };
    const awaitWaiters = async (count: number) => {
      for (let i = 0; i < 40; i++) {
        if (await countWaiting() === count) return;
        await delay(25);
      }
      assert.fail(`Expected ${count} blocked reads on PostgreSQL`);
    };
    const timedBlocked = async () => {
      const start = performance.now();
      await assert.rejects(blocked(), (error) => (error as { code?: string }).code === "57014");
      return Math.round(performance.now() - start);
    };

    const first = timedBlocked();
    void first.catch(() => {});
    await awaitWaiters(1);
    const health = await buildHealthResponse();
    assert.equal(health.status, "healthy");
    const lockedMs = await first;
    assert.ok(lockedMs <= DATABASE_READ_DEADLINE_MS + 250, `Blocked read took ${lockedMs}ms`);
    assert.equal(await countWaiting(), 0);
    console.log(`One blocked read aborted with SQLSTATE 57014 after ${lockedMs}ms; health succeeded during lock`);

    const concurrent = [timedBlocked(), timedBlocked()];
    const pending = Promise.all(concurrent);
    void pending.catch(() => {});
    await awaitWaiters(2);
    await delay(750);
    const queuedStart = performance.now();
    const queued = Promise.all([1, 2, 3].map(
      (value) => queryValues<{ value: number }>("SELECT $1::int AS value", [value]),
    ));
    const [durations, rows] = await Promise.all([pending, queued]);
    assert.deepEqual(rows.map((result) => result[0].value), [1, 2, 3]);
    assert.equal(await countWaiting(), 0);
    assert.ok(durations.every((duration) => duration <= DATABASE_READ_DEADLINE_MS + 250));
    console.log(`Two blocked reads aborted after ${durations.join("/")}ms; three queued reads recovered in ${Math.round(performance.now() - queuedStart)}ms`);

    const qualityStart = performance.now();
    assert.deepEqual(await getQualitySummaries(), { datasets: [], message: "Data quality is unavailable." });
    console.log(`Locked quality read returned unavailable in ${Math.round(performance.now() - qualityStart)}ms`);
    assert.equal((await query<{ value: number }>("SELECT 1 AS value"))[0].value, 1);
    const [settings] = await control`SELECT current_setting('statement_timeout') AS timeout`;
    const [after] = await query<{ timeout: string }>("SELECT current_setting('statement_timeout') AS timeout");
    assert.notEqual(after.timeout, settings.timeout, "The deadline must apply inside the transaction");
    const [poolSession] = await getPool()`SELECT current_setting('statement_timeout') AS timeout`;
    assert.equal(poolSession.timeout, settings.timeout, "The transaction timeout must not leak to the pooled session");
    const connections = await Promise.all([getPool().reserve(), getPool().reserve()]);
    try {
      await Promise.all(connections.map((connection) => connection`SET statement_timeout = '200ms'`));
    } finally {
      for (const connection of connections) connection.release();
    }
    const shorterStart = performance.now();
    await assert.rejects(query("SELECT pg_sleep(1)"), (error) => (error as { code?: string }).code === "57014");
    const shorterMs = Math.round(performance.now() - shorterStart);
    assert.ok(shorterMs < 800, `Existing shorter timeout was widened to ${shorterMs}ms`);
    console.log(`An existing shorter server timeout stayed effective at ${shorterMs}ms`);
  } finally {
    await locked`ROLLBACK`;
    locked.release();
    await control.end({ timeout: 2 });
    await getPool().end({ timeout: 2 });
  }
});
