import { describe, it, expect } from "vitest";
import {
  getPageIndex,
  rubberBand,
  getNavPath,
  resolveDiaryPath,
} from "../src/lib/navigation";
import { http, HttpResponse } from "msw";
import { server } from "./setup";
import { getMockDate } from "../src/lib/mockDate";

describe("getPageIndex", () => {
  it.each([
    ["/diary/2026-05-29", 0],
    ["/qna/2026-05-29", 0],
    ["/hub", 1],
    ["/calendar", 2],
    ["/profile", 3],
    ["/search", -1],
    ["/schedule/1", -1],
    ["/admin", -1],
  ])("%s → %i", (path, expected) => {
    expect(getPageIndex(path)).toBe(expected);
  });
});

describe("rubberBand", () => {
  it("dampens at 0.25× up to default max 60", () => {
    expect(rubberBand(100)).toBeCloseTo(25);
    expect(rubberBand(-100)).toBeCloseTo(-25);
  });
  it("caps at default max 60", () => {
    expect(rubberBand(400)).toBe(60);
    expect(rubberBand(-400)).toBe(-60);
  });
  it("honours custom max", () => {
    expect(rubberBand(200, 40)).toBe(40);
  });
});

describe("getNavPath", () => {
  it("returns sync paths for indices 1–3", () => {
    expect(getNavPath(1)).toBe("/hub");
    expect(getNavPath(2)).toBe("/calendar");
    expect(getNavPath(3)).toBe("/profile");
  });
  it("returns null for diary index 0 (async)", () => {
    expect(getNavPath(0)).toBeNull();
  });
});

describe("resolveDiaryPath", () => {
  const today = "2026-05-29";

  it("returns /diary/:today when entry exists for today", async () => {
    server.use(
      http.get("/api/calendar", () =>
        HttpResponse.json({
          entries: [{ date: today }],
          schedules: [],
        }),
      ),
    );
    const result = await resolveDiaryPath(today);
    expect(result).toBe(`/diary/${today}`);
  });

  it("returns /qna/:today when no entry exists for today", async () => {
    server.use(
      http.get("/api/calendar", () =>
        HttpResponse.json({
          entries: [],
          schedules: [],
        }),
      ),
    );
    const result = await resolveDiaryPath(today);
    expect(result).toBe(`/qna/${today}`);
  });

  it("returns /qna/:today on API error", async () => {
    server.use(
      http.get("/api/calendar", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );
    const result = await resolveDiaryPath(today);
    expect(result).toBe(`/qna/${today}`);
  });
});
