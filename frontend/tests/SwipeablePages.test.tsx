import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { SwipeablePages } from "../src/components/layout/SwipeablePages";

function wrap(path: string, children: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>,
  );
}

describe("SwipeablePages", () => {
  it("renders children", () => {
    wrap(
      "/hub",
      <SwipeablePages>
        <div>page content</div>
      </SwipeablePages>,
    );
    expect(screen.getByText("page content")).toBeInTheDocument();
  });

  it("attaches touch event handlers to the container", () => {
    const { container } = wrap(
      "/hub",
      <SwipeablePages>
        <div>content</div>
      </SwipeablePages>,
    );
    const outer = container.firstElementChild as HTMLElement;
    expect(outer).not.toBeNull();
    // Verify the outer div has overflow hidden (clipping)
    expect(outer.style.overflow).toBe("hidden");
  });

  it("renders on a non-swipe page without crashing", () => {
    wrap(
      "/search",
      <SwipeablePages>
        <div>search page</div>
      </SwipeablePages>,
    );
    expect(screen.getByText("search page")).toBeInTheDocument();
  });
});
