import { getSessionId } from '../api/client'

export type LadderUndoStep = {
  fromProductId: number
  toProductId: number
  pointsAwarded?: number
}

function storageKey(): string {
  return `sipmate_ladder_stack:${getSessionId()}`
}

export function getLadderStack(): LadderUndoStep[] {
  try {
    const raw = sessionStorage.getItem(storageKey())
    if (!raw) return []
    const parsed = JSON.parse(raw) as LadderUndoStep[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveStack(stack: LadderUndoStep[]): void {
  sessionStorage.setItem(storageKey(), JSON.stringify(stack))
}

export function pushLadderStep(step: LadderUndoStep): void {
  const stack = getLadderStack()
  stack.push(step)
  saveStack(stack)
}

export function popLadderStep(): LadderUndoStep | null {
  const stack = getLadderStack()
  const step = stack.pop() ?? null
  saveStack(stack)
  return step
}

export function clearLadderStack(): void {
  sessionStorage.removeItem(storageKey())
}

export function hasLadderUndo(): boolean {
  return getLadderStack().length > 0
}

/** First accepted-from drink this round; else the current product. */
export function getRoundOriginId(currentProductId: number): number {
  const stack = getLadderStack()
  if (stack.length === 0) return currentProductId
  return stack[0].fromProductId
}

export function getRoundPoints(): number {
  return getLadderStack().reduce((sum, step) => sum + (step.pointsAwarded ?? 0), 0)
}
