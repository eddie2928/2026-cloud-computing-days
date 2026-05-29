import { useState, useRef, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useMockDate } from "./useMockDate";
import {
  getPageIndex,
  rubberBand,
  getNavPath,
  resolveDiaryPath,
} from "../lib/navigation";

export type SwipePhase = "idle" | "dragging" | "exiting" | "entering";

export interface SwipeNavState {
  offset: number;
  phase: SwipePhase;
  swipeDirection: "left" | "right" | null;
  handlers: {
    onTouchStart: (e: React.TouchEvent) => void;
    onTouchMove: (e: React.TouchEvent) => void;
    onTouchEnd: () => void;
    onTransitionEnd: (e: React.TransitionEvent) => void;
    onAnimationEnd: () => void;
  };
}

const SNAP_THRESHOLD = 0.4;
const LOCK_DISTANCE = 15;

export function useSwipeNavigation(): SwipeNavState {
  const location = useLocation();
  const navigate = useNavigate();
  const today = useMockDate();

  const [offset, setOffset] = useState(0);
  const [phase, setPhase] = useState<SwipePhase>("idle");
  const [swipeDirection, setSwipeDirection] = useState<"left" | "right" | null>(
    null,
  );

  const startX = useRef(0);
  const startY = useRef(0);
  const directionLock = useRef<"horizontal" | "vertical" | null>(null);
  const currentIndex = useRef(-1);
  const pendingDiaryPath = useRef<Promise<string> | null>(null);

  const onTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (phase !== "idle") return;
      const idx = getPageIndex(location.pathname);
      if (idx === -1) return;
      currentIndex.current = idx;
      startX.current = e.touches[0].clientX;
      startY.current = e.touches[0].clientY;
      directionLock.current = null;
    },
    [phase, location.pathname],
  );

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (currentIndex.current === -1) return;

    const dx = e.touches[0].clientX - startX.current;
    const dy = e.touches[0].clientY - startY.current;

    if (!directionLock.current) {
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < LOCK_DISTANCE) return;
      directionLock.current =
        Math.abs(dx) > Math.abs(dy) * 1.5 ? "horizontal" : "vertical";
    }
    if (directionLock.current !== "horizontal") return;

    const idx = currentIndex.current;
    const atStart = idx === 0 && dx > 0;
    const atEnd = idx === 3 && dx < 0;
    const newOffset = atStart || atEnd ? rubberBand(dx) : dx;
    const dir: "left" | "right" = dx < 0 ? "left" : "right";

    setOffset(newOffset);
    setSwipeDirection(dir);
    setPhase("dragging");
  }, []);

  const onTouchEnd = useCallback(() => {
    if (phase !== "dragging") return;

    const idx = currentIndex.current;
    const threshold = window.innerWidth * SNAP_THRESHOLD;
    const canSnap =
      (offset < -threshold && idx < 3) || (offset > threshold && idx > 0);

    if (canSnap) {
      const targetIndex = offset < 0 ? idx + 1 : idx - 1;
      // Pre-fetch diary path so it's ready when transition ends (220ms window)
      if (targetIndex === 0) {
        pendingDiaryPath.current = resolveDiaryPath(today);
      }
      setPhase("exiting");
    } else {
      setOffset(0);
      setPhase("idle");
    }
  }, [phase, offset, today]);

  const onTransitionEnd = useCallback(
    async (e: React.TransitionEvent) => {
      if (phase !== "exiting" || e.propertyName !== "transform") return;

      const idx = currentIndex.current;
      const targetIndex = swipeDirection === "left" ? idx + 1 : idx - 1;

      const syncPath = getNavPath(targetIndex);
      const path = syncPath
        ? syncPath
        : await (pendingDiaryPath.current ?? resolveDiaryPath(today));

      pendingDiaryPath.current = null;
      setOffset(0);
      setPhase("entering");
      navigate(path);
    },
    [phase, swipeDirection, navigate, today],
  );

  const onAnimationEnd = useCallback(() => {
    if (phase !== "entering") return;
    setPhase("idle");
    setSwipeDirection(null);
    currentIndex.current = -1;
  }, [phase]);

  return {
    offset,
    phase,
    swipeDirection,
    handlers: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
      onTransitionEnd,
      onAnimationEnd,
    },
  };
}
