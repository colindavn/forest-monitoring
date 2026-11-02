/** ColorBrewer YlOrRd, 6 classes (sequential, colour-blind safe). */
export const PALETTE = ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026'] as const
export const NO_DATA_COLOR = '#d9d9d9'

type Value = number | null | undefined

function isValue(v: Value): v is number {
  return v != null && Number.isFinite(v)
}

/** Quantile class breaks (k classes → up to k-1 ascending, de-duplicated breaks). */
export function quantileBreaks(values: Value[], classes: number = PALETTE.length): number[] {
  const sorted = values.filter(isValue).sort((a, b) => a - b)
  if (sorted.length === 0) return []
  const breaks: number[] = []
  for (let i = 1; i < classes; i++) {
    const v = sorted[Math.floor((i * sorted.length) / classes)]
    if (v !== undefined && breaks[breaks.length - 1] !== v) breaks.push(v)
  }
  return breaks
}

/** Class index of `value` (number of breaks <= value), or -1 when missing. */
export function classify(value: Value, breaks: number[]): number {
  if (!isValue(value)) return -1
  return breaks.filter((b) => b <= value).length
}

export function colorFor(value: Value, breaks: number[]): string {
  const i = classify(value, breaks)
  return i < 0 ? NO_DATA_COLOR : PALETTE[Math.min(i, PALETTE.length - 1)]
}
