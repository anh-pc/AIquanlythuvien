import test from "node:test";
import assert from "node:assert/strict";
import {
  buildBooksQueryString,
  createDebounce,
  createRaceGuard,
} from "../src/utils/bookSearchHelper.js";

test("buildBooksQueryString trims keyword and includes category_id and page", () => {
  const qs1 = buildBooksQueryString({ keyword: "  python  ", categoryId: 2, page: 1, pageSize: 5 });
  assert.equal(qs1, "keyword=python&category_id=2&page=1&page_size=5");

  const qs2 = buildBooksQueryString({ keyword: "   ", categoryId: null, page: 3, pageSize: 5 });
  assert.equal(qs2, "page=3&page_size=5");
});

test("createDebounce coalesces rapid calls and supports flush/cancel", async () => {
  let callCount = 0;
  let lastArg = null;
  const debounced = createDebounce((val) => {
    callCount += 1;
    lastArg = val;
  }, 40);

  debounced("p");
  debounced("py");
  debounced("python");

  await new Promise((r) => setTimeout(r, 80));
  assert.equal(callCount, 1);
  assert.equal(lastArg, "python");

  // Flush executes immediately and cancels pending timer
  debounced("pending");
  debounced.flush("immediate");
  assert.equal(callCount, 2);
  assert.equal(lastArg, "immediate");
});

test("createRaceGuard invalidates older tokens and aborts previous signal", () => {
  const guard = createRaceGuard();
  const req1 = guard.next();
  assert.equal(guard.isLatest(req1.token), true);
  assert.equal(req1.signal.aborted, false);

  const req2 = guard.next();
  assert.equal(guard.isLatest(req1.token), false);
  assert.equal(req1.signal.aborted, true);
  assert.equal(guard.isLatest(req2.token), true);
});
