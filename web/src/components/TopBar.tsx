import type { Health } from '../api/client'
import { METRIC_LABELS, YEARLY_METRICS } from '../lib/labels'
import { METRICS, THRESHOLDS, type Metric, type Threshold } from '../lib/route'
import type { Layers } from '../map/MapView'

interface Props {
  metric: Metric
  year: number
  latestYear: number
  threshold: Threshold
  layers: Layers
  health: Health | null
  onMetric: (m: Metric) => void
  onYear: (y: number) => void
  onThreshold: (t: Threshold) => void
  onLayers: (l: Layers) => void
  onAbout: () => void
}

export default function TopBar(p: Props) {
  const yearly = YEARLY_METRICS.includes(p.metric)
  const toggle = (key: 'choropleth' | 'hansen' | 'alerts' | 'alertsHighOnly') =>
    p.onLayers({ ...p.layers, [key]: !p.layers[key] })

  return (
    <header className="topbar">
      <h1>Perte de couvert arboré et perturbations forestières en France</h1>
      <div className="controls">
        <label>
          Indicateur
          <select value={p.metric} onChange={(e) => p.onMetric(e.target.value as Metric)}>
            {METRICS.map((m) => (
              <option key={m} value={m}>
                {METRIC_LABELS[m]}
              </option>
            ))}
          </select>
        </label>

        <label className={yearly ? '' : 'disabled'}>
          Année <output>{p.year}</output>
          <input
            type="range"
            min={2001}
            max={p.latestYear}
            value={p.year}
            disabled={!yearly}
            onChange={(e) => p.onYear(Number(e.target.value))}
            aria-valuetext={String(p.year)}
          />
        </label>

        <fieldset className="segmented">
          <legend>Seuil de couvert</legend>
          {THRESHOLDS.map((t) => (
            <label key={t}>
              <input
                type="radio"
                name="threshold"
                checked={p.threshold === t}
                onChange={() => p.onThreshold(t)}
              />
              {t}&nbsp;%
            </label>
          ))}
        </fieldset>

        <fieldset className="layers">
          <legend>Couches</legend>
          <label>
            <input
              type="checkbox"
              checked={p.layers.choropleth}
              onChange={() => toggle('choropleth')}
            />
            Choroplèthe
          </label>
          <label>
            <input type="checkbox" checked={p.layers.hansen} onChange={() => toggle('hansen')} />
            Pixels de perte (Hansen)
          </label>
          <label>
            <input type="checkbox" checked={p.layers.alerts} onChange={() => toggle('alerts')} />
            Alertes récentes (DIST-ALERT, 90 j)
          </label>
          {p.layers.alerts && (
            <label>
              <input
                type="checkbox"
                checked={p.layers.alertsHighOnly}
                onChange={() => toggle('alertsHighOnly')}
              />
              Haute confiance seulement
            </label>
          )}
          <label>
            Fond
            <select
              value={p.layers.basemap}
              onChange={(e) =>
                p.onLayers({ ...p.layers, basemap: e.target.value as Layers['basemap'] })
              }
            >
              <option value="plan">Plan IGN</option>
              <option value="ortho">Orthophoto IGN</option>
            </select>
          </label>
        </fieldset>

        <div className="freshness" aria-live="polite">
          {p.health && (
            <>
              Hansen jusqu’à {p.health.latest_loss_year ?? '—'} · alertes jusqu’au{' '}
              {p.health.latest_alert_date ?? '—'}
            </>
          )}
        </div>
        <button type="button" className="about-btn" onClick={p.onAbout}>
          À propos des données
        </button>
      </div>
    </header>
  )
}
