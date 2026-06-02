import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MonthGrid } from "../src/components/calendar/MonthGrid";
import { getSeoulToday } from "../src/lib/today";

const noop = vi.fn();

describe("MonthGrid", () => {
  it("2026-05 → 6개 주행(week-row), 각 행 7개 셀 = 총 42개 (7×6)", () => {
    render(
      <MonthGrid
        year={2026}
        month={5}
        entries={[]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const grid = screen.getByTestId("month-grid");
    expect(grid.children).toHaveLength(6); // 6 week rows
    const dateCells = grid.querySelectorAll("button[aria-label]");
    expect(dateCells).toHaveLength(42); // 7×6 date cells
  });

  it("일요일 시작 — 첫 셀이 일요일(일)", () => {
    render(
      <MonthGrid
        year={2026}
        month={5}
        entries={[]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    // 2026-05-01은 금요일(5). 첫 셀은 4/26(일요일).
    const cells = screen.getAllByRole("button", { name: /2026-04-26/ });
    expect(cells).toHaveLength(1);
  });

  it("이전/다음 달 네비 버튼 존재", () => {
    render(
      <MonthGrid
        year={2026}
        month={5}
        entries={[]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    expect(screen.getByLabelText("이전 달")).toBeInTheDocument();
    expect(screen.getByLabelText("다음 달")).toBeInTheDocument();
  });

  it("당일 작성 일기 — solid 초록 border", () => {
    render(
      <MonthGrid
        year={2026}
        month={1}
        entries={[
          { date: "2026-01-15", emotion: "happy", written_date: "2026-01-15" },
        ]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText("2026-01-15");
    expect(cell.style.border).toBe("2px solid var(--sage-leaf)");
  });

  it("다른날 작성 일기 — dashed 초록 border", () => {
    render(
      <MonthGrid
        year={2026}
        month={1}
        entries={[
          { date: "2026-01-15", emotion: "happy", written_date: "2026-01-16" },
        ]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText("2026-01-15");
    expect(cell.style.border).toBe("2px dashed var(--sage-leaf)");
  });

  it("일기 없는 날 — border 없음", () => {
    render(
      <MonthGrid
        year={2026}
        month={1}
        entries={[]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText("2026-01-15");
    expect(cell.style.border).toBe("1px solid transparent");
  });

  it("written_date 없는 entry — fallback solid 초록 border", () => {
    render(
      <MonthGrid
        year={2026}
        month={1}
        entries={[{ date: "2026-01-15", emotion: "happy" }]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText("2026-01-15");
    expect(cell.style.border).toBe("2px solid var(--sage-leaf)");
  });

  it("오늘 날짜 — sage-forest solid border", () => {
    const today = getSeoulToday();
    const [y, m] = today.split("-").map(Number);
    render(
      <MonthGrid
        year={y}
        month={m}
        entries={[]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText(today);
    expect(cell.style.border).toBe("2px solid var(--sage-forest)");
  });

  it("오늘이면서 일기도 있는 날 — today 스타일 우선", () => {
    const today = getSeoulToday();
    const [y, m] = today.split("-").map(Number);
    render(
      <MonthGrid
        year={y}
        month={m}
        entries={[{ date: today, emotion: "happy", written_date: today }]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />,
    );
    const cell = screen.getByLabelText(today);
    expect(cell.style.border).toBe("2px solid var(--sage-forest)");
  });
});
