import assert from "node:assert/strict";
import test from "node:test";
import { ageText, utcTime } from "../lib/time";

test("timestamps and ages are explicit and handle missing or future values", () => {
  const now = Date.parse("2026-11-14T12:00:00Z");
  assert.equal(utcTime("2026-11-14T11:00:00Z"), "2026-11-14 11:00:00 UTC");
  assert.equal(ageText("2026-11-14T11:00:00Z", now), "1 hr old");
  assert.equal(ageText(null, now), "age unknown");
  assert.equal(ageText("2026-11-14T13:00:00Z", now), "timestamp is in the future");
});
