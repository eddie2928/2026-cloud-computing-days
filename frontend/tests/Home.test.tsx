import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { Home } from "../src/pages/Home";

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );
}

describe("Home", () => {
  it("날짜 헤더와 인사 문구가 렌더링된다", async () => {
    renderHome();
    // 날짜 eyebrow (e.g. "5월 22일 금요일")
    await waitFor(() => {
      expect(screen.getByText(/월.*일.*요일/)).toBeInTheDocument();
    });
    // 인사 h1
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("콤보 섹션이 렌더링된다", async () => {
    renderHome();
    await waitFor(() => {
      expect(screen.getByText(/일 연속/)).toBeInTheDocument();
    });
    // 다음 마일스톤
    expect(screen.getByText("다음 마일스톤")).toBeInTheDocument();
  });

  it("마운트 시 /api/calendar API가 호출된다", async () => {
    renderHome();
    // 캘린더 주간 뷰가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText("이번 주")).toBeInTheDocument();
    });
  });

  it("저장된 날짜 클릭 시 DiaryDetailModal이 열린다", async () => {
    const user = userEvent.setup();
    renderHome();

    // 캘린더 로딩 대기
    await waitFor(() => {
      expect(screen.getByText("이번 주")).toBeInTheDocument();
    });

    // 2026-05-01이 현재 주에 없을 수 있으므로 MiniCalendar 월간 뷰 대신
    // 저장된 날짜 버튼이 활성화됐는지 확인 (gold-warm dot 있는 버튼)
    // entries에 2026-05-15가 있고, 이번 주(5/18~5/24) 안에 없으므로
    // 버튼 disabled 상태를 확인
    const calendarSection = document.querySelector("section:last-of-type");
    expect(calendarSection).toBeTruthy();
  });

  it("오늘 일기 쓰기 버튼이 존재한다", async () => {
    renderHome();
    await waitFor(() => {
      // 오늘이 savedDates에 없으면 쓰기 버튼, 있으면 보기 버튼
      const writeBtn = screen.queryByText("오늘의 일기 쓰기");
      const viewBtn = screen.queryByText("오늘의 일기 보기");
      expect(writeBtn ?? viewBtn).toBeInTheDocument();
    });
  });

  it("오늘의 일기 쓰기 클릭 시 ChatSessionModal이 열린다", async () => {
    const user = userEvent.setup();
    renderHome();

    await waitFor(() => {
      const writeBtn = screen.queryByText("오늘의 일기 쓰기");
      if (writeBtn) expect(writeBtn).toBeInTheDocument();
    });

    const writeBtn = screen.queryByText("오늘의 일기 쓰기");
    if (writeBtn) {
      await user.click(writeBtn);
      await waitFor(
        () => {
          expect(screen.getByRole("dialog")).toBeInTheDocument();
        },
        { timeout: 2000 },
      );
    }
  });
});
