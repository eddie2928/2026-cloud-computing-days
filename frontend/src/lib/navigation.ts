import client from "../api/client";

export function getPageIndex(pathname: string): number {
  if (pathname.startsWith("/diary") || pathname.startsWith("/qna")) return 0;
  if (pathname === "/hub") return 1;
  if (pathname === "/calendar") return 2;
  if (pathname === "/profile") return 3;
  return -1;
}

export function rubberBand(delta: number, max = 60): number {
  return Math.sign(delta) * Math.min(Math.abs(delta) * 0.25, max);
}

/** Returns the sync navigation path for pages 1-3; null for diary (needs async). */
export function getNavPath(targetIndex: number): string | null {
  if (targetIndex === 1) return "/hub";
  if (targetIndex === 2) return "/calendar";
  if (targetIndex === 3) return "/profile";
  return null;
}

/** Mirrors BottomNav diary-tap logic: checks today's entry, returns /diary or /qna path. */
export async function resolveDiaryPath(today: string): Promise<string> {
  try {
    const month = today.slice(0, 7);
    const res = await client.get(`/calendar?month=${month}`);
    const entries: { date: string }[] = res.data?.entries ?? [];
    return entries.some((e) => e.date === today)
      ? `/diary/${today}`
      : `/qna/${today}`;
  } catch {
    return `/qna/${today}`;
  }
}
