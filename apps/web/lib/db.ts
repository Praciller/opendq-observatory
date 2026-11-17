import postgres, { type Sql } from "postgres";

import { databaseUrl } from "./config";

export const DATABASE_READ_DEADLINE_MS = 5_000;
const ROLLBACK_HEADROOM_MS = 250;
const POOL_RECOVERY_GRACE_MS = 1_000;
const POOL_SIZE = 2;

let client: Sql | undefined;
let inFlight = 0;
const waitingReads = new Set<() => void>();

export function getPool(): Sql {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not configured");
  }
  client ??= postgres(databaseUrl, {
    connect_timeout: 5,
    idle_timeout: 10,
    max: POOL_SIZE,
  });
  return client;
}

export async function query<T extends Record<string, unknown>>(
  text: string,
): Promise<T[]> {
  return queryValues<T>(text, []);
}

export async function queryValues<T extends Record<string, unknown>>(
  text: string,
  values: unknown[],
): Promise<T[]> {
  const deadline = performance.now() + DATABASE_READ_DEADLINE_MS;
  const timeout = new Error("Database read deadline exceeded");

  return new Promise<T[]>((resolve, reject) => {
    let pool: Sql | undefined;
    let recovery: ReturnType<typeof setTimeout> | undefined;
    const timer = setTimeout(() => {
      waitingReads.delete(start);
      reject(timeout);
      const stalledPool = pool;
      if (!stalledPool) return;

      // The server normally aborts the statement and rolls back before this point.
      // Retire this pool if the transport or rollback stops responding.
      recovery = setTimeout(() => {
        if (client !== stalledPool) return;
        client = undefined;
        void stalledPool.end({ timeout: 0 }).catch(() => {});
      }, POOL_RECOVERY_GRACE_MS);
    }, DATABASE_READ_DEADLINE_MS);

    function start() {
      if (performance.now() >= deadline) {
        clearTimeout(timer);
        reject(timeout);
        return;
      }

      inFlight++;
      void (async () => {
        pool = getPool();
        return pool.begin("read only", async (transaction) => {
          const statementBudget = Math.floor(deadline - performance.now()) - ROLLBACK_HEADROOM_MS;
          if (statementBudget <= 0) throw timeout;
          // Keep the timeout local to this transaction, including behind a transaction pooler.
          await transaction`
            SELECT set_config('statement_timeout',
              LEAST(${statementBudget}::integer, COALESCE(NULLIF(setting::integer, 0), ${statementBudget}::integer))::text,
              true)
            FROM pg_settings
            WHERE name = 'statement_timeout'`;
          if (deadline - performance.now() <= ROLLBACK_HEADROOM_MS) throw timeout;
          const rows = await transaction.unsafe<T[]>(text, values as never[]);
          return { rows };
        });
      })().then(({ rows }) => {
        if (performance.now() >= deadline) reject(timeout);
        else resolve(rows);
      }, reject).finally(() => {
        clearTimeout(timer);
        clearTimeout(recovery);
        inFlight--;
        startWaitingReads();
      });
    }

    waitingReads.add(start);
    startWaitingReads();
  });
}

function startWaitingReads() {
  // Hold each permit until the driver releases its transaction. Expired waiters
  // stay out of the driver's queue and cannot execute after a slot frees up.
  for (const start of waitingReads) {
    if (inFlight >= POOL_SIZE) break;
    waitingReads.delete(start);
    start();
  }
}
