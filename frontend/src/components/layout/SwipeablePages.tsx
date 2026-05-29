import type { ReactNode } from "react";
import { useSwipeNavigation } from "../../hooks/useSwipeNavigation";

export function SwipeablePages({ children }: { children: ReactNode }) {
  const { offset, phase, swipeDirection, handlers } = useSwipeNavigation();

  const isDragging = phase === "dragging";
  const isExiting = phase === "exiting";
  const isEntering = phase === "entering";

  const transform = isDragging
    ? `translateX(${offset}px)`
    : isExiting
      ? `translateX(${swipeDirection === "left" ? "-110%" : "110%"})`
      : undefined;

  const transition = isExiting ? "transform 220ms ease-in" : undefined;

  const animation = isEntering
    ? `${swipeDirection === "left" ? "page-from-right" : "page-from-left"} 280ms var(--ease-out) both`
    : undefined;

  return (
    <div
      style={{
        overflow: "hidden",
        flex: 1,
        display: "flex",
        flexDirection: "column",
      }}
      onTouchStart={handlers.onTouchStart}
      onTouchMove={handlers.onTouchMove}
      onTouchEnd={handlers.onTouchEnd}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          ...(transform !== undefined && { transform }),
          ...(transition !== undefined && { transition }),
          ...(animation !== undefined && { animation }),
          ...(isDragging && { willChange: "transform" }),
        }}
        onTransitionEnd={handlers.onTransitionEnd}
        onAnimationEnd={handlers.onAnimationEnd}
      >
        {children}
      </div>
    </div>
  );
}
