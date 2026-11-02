const MISSING = '—'

const haSmall = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })
const haLarge = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 })
const pct = new Intl.NumberFormat('fr-FR', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Hectares in French format, e.g. "12 345,6 ha". */
export function formatHa(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return MISSING
  const fmt = Math.abs(value) >= 100_000 ? haLarge : haSmall
  return `${fmt.format(value)} ha`
}

/** Ratio (0.0123) as French percentage, e.g. "1,23 %". */
export function formatPct(ratio: number | null | undefined): string {
  if (ratio == null || Number.isNaN(ratio)) return MISSING
  return pct.format(ratio)
}
