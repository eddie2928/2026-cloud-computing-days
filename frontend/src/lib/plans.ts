export type PlanSource = 'manual' | 'ai';

export interface PlanOut {
  id: number;
  user_id: number;
  title: string;
  description_input: string | null;
  goal_input: string | null;
  period_start: string;  // 'YYYY-MM-DD'
  period_end: string;    // 'YYYY-MM-DD'
  source: PlanSource;
  created_at: string;    // ISO 8601
  progress: number;      // 0~1
}

export interface PlanTodoOut {
  id: number;
  plan_id: number;
  todo_date: string;     // 'YYYY-MM-DD'
  sequence: number;
  content: string;
  completed: boolean;
  completed_at: string | null;
}

export interface PlanWithTodosOut extends PlanOut {
  todos: PlanTodoOut[];
}

export interface PlanCreateInput {
  title: string;
  period_start: string;
  period_end: string;
  description_input?: string;
  goal_input?: string;
}

export interface PlanUpdateInput {
  title?: string;
  period_start?: string;
  period_end?: string;
  description_input?: string;
  goal_input?: string;
}

export interface PlanTodoCreateInput {
  todo_date: string;
  sequence?: number;
  content: string;
}

export interface PlanTodoUpdateInput {
  sequence?: number;
  content?: string;
  completed?: boolean;
}

export interface PlanGenerateInput {
  description: string;
  period_start: string;
  period_end: string;
  goal: string;
}

/** Returns progress as an integer 0–100 (rounded). */
export function planProgressPercent(plan: PlanOut): number {
  return Math.round(plan.progress * 100);
}

/** Groups todos by their todo_date key ('YYYY-MM-DD'). */
export function todosByDate(todos: PlanTodoOut[]): Record<string, PlanTodoOut[]> {
  const result: Record<string, PlanTodoOut[]> = {};
  for (const todo of todos) {
    if (!result[todo.todo_date]) {
      result[todo.todo_date] = [];
    }
    result[todo.todo_date].push(todo);
  }
  return result;
}

/**
 * Returns an array of 'YYYY-MM-DD' strings from start to end inclusive.
 * If start > end, returns empty array.
 */
export function dateRangeInclusive(start: string, end: string): string[] {
  const dates: string[] = [];
  const cur = new Date(start);
  const last = new Date(end);
  while (cur <= last) {
    dates.push(cur.toISOString().slice(0, 10));
    cur.setDate(cur.getDate() + 1);
  }
  return dates;
}

/** Simple string-level same-day check ('YYYY-MM-DD' prefix equality). */
export function isSameLocalDay(a: string, b: string): boolean {
  return a.slice(0, 10) === b.slice(0, 10);
}
