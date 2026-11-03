import { METRIC_LABELS, formatMetric } from '../lib/labels'
import type { Metric } from '../lib/route'
import { NO_DATA_COLOR, PALETTE } from '../lib/scale'

export default function Legend({ metric, breaks }: { metric: Metric; breaks: number[] }) {
  const classes = breaks.length + 1
  const label = (i: number) => {
    if (i === 0) return `< ${formatMetric(metric, breaks[0])}`
    if (i === classes - 1) return `≥ ${formatMetric(metric, breaks[i - 1])}`
    return `${formatMetric(metric, breaks[i - 1])} – ${formatMetric(metric, breaks[i])}`
  }
  return (
    <div className="legend" aria-label="Légende de la carte">
      <div className="legend-title">{METRIC_LABELS[metric]}</div>
      <ul>
        {breaks.length > 0 &&
          Array.from({ length: classes }, (_, i) => (
            <li key={i}>
              <span className="swatch" style={{ background: PALETTE[i] }} />
              {label(i)}
            </li>
          ))}
        <li>
          <span className="swatch" style={{ background: NO_DATA_COLOR }} />
          Pas de données
        </li>
      </ul>
    </div>
  )
}
