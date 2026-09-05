import postgres, { type Sql } from "postgres";

import { databaseUrl } from "./config";

let client: Sql | undefined;

export function getPool(): Sql {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not configured");
  }
  client ??= postgres(databaseUrl, {
    connect_timeout: 1,
    idle_timeout: 10,
    max: 2,
  });
  return client;
}

export async function query<T extends Record<string, unknown>>(
  text: string,
): Promise<T[]> {
  return getPool().unsafe<T[]>(text);
}
