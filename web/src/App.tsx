import { useCallback, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, type AreaKpis } from './api/client'
import AlertsChart from './charts/AlertsChart'
import LossChart from './charts/LossChart'
import AboutPanel from './components/AboutPanel'
import KpiCards from './components/KpiCards'
import Legend from './components/Legend'
import RankingTable from './components/RankingTable'
import TopBar from './components/TopBar'
import { downloadCsv, toCsv } from './lib/csv'
import { YEARLY_METRICS } from './lib/labels'
import { parseView, viewToUrl, type Level, type View } from './lib/route'
import { quantileBreaks } from './lib/scale'
import { useAsync } from './lib/useAsync'
import MapView, { type Layers } from './map/MapView'
import { loadGeo } from './map/geo'

const DEFAULT_LAYERS: Layers = {
  choropleth: true,
  hansen: false,
  alerts: false,
  alertsHighOnly: false,
  basemap: 'plan',
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const view = parseView(location.pathname, location.search)
  const go = useCallback(
    (next: Partial<View>) => navigate(viewToUrl({ ...view, ...next })),
    [navigate, view],
  )
  const [layers, setLayers] = useState(DEFAULT_LAYERS)
  const [about, setAbout] = useState(false)

  const health = useAsync(() => api.health(), [])
  const meta = useAsync(() => api.meta(), [])
  const geo = useAsync(() => Promise.all([loadGeo('regions'), loadGeo('departments')]), [])
  const { level, code, threshold, metric } = view
  const area = useAsync(() => api.area(level, code, threshold), [level, code, threshold])
  const loss = useAsync(() => api.loss(level, code, threshold), [level, code, threshold])
  const alerts = useAsync(() => api.alerts(level, code, threshold), [level, code, threshold])

  const latestYear = health.data?.latest_loss_year ?? 2025
  const year = view.year ?? latestYear
  const regionCode =
    level === 'region' ? code : level === 'department' ? (area.data?.parent?.code ?? null) : null
  const mapLevel = level === 'france' ? 'region' : 'department'
  const yearParam = YEARLY_METRICS.includes(metric) ? year : null
  const choropleth = useAsync(
    level !== 'france' && !regionCode
      ? null
      : () => api.choropleth(mapLevel, metric, threshold, yearParam, regionCode),
    [mapLevel, metric, threshold, yearParam, regionCode],
  )
  const values = useMemo(() => choropleth.data?.values ?? {}, [choropleth.data])
  const breaks = useMemo(() => quantileBreaks(Object.values(values)), [values])

  const select = useCallback((lvl: Level, c: string) => go({ level: lvl, code: c }), [go])
  const selectChild = (a: AreaKpis) => select(a.level, a.code)
  const lossYears = useMemo<[number, number]>(
    () => [2001, YEARLY_METRICS.includes(metric) ? year : latestYear],
    [metric, year, latestYear],
  )

  const kpis = area.data?.area
  const exportLoss = () =>
    loss.data &&
    downloadCsv(
      `perte_${level}_${code}_seuil${threshold}.csv`,
      toCsv(loss.data.series, [
        'year',
        'forest_2000_ha',
        'loss_ha',
        'loss_pct_of_2000',
        'cum_loss_ha',
        'loss_ha_5y_avg',
      ]),
    )
  const exportAlerts = () =>
    alerts.data &&
    downloadCsv(
      `alertes_${level}_${code}_seuil${threshold}.csv`,
      toCsv(alerts.data.series, [
        'week_start',
        'area_ha_nominal',
        'area_ha_high',
        'area_ha_highest',
        'area_ha_all',
        'area_ha_4w_rolling',
        'z_score',
        'is_anomaly',
      ]),
    )

  return (
    <div className="app">
      {health.data?.synthetic && (
        <div className="banner" role="alert">
          Données de démonstration (SYNTHÉTIQUES) — les chiffres affichés sont fictifs.
        </div>
      )}
      <TopBar
        metric={metric}
        year={year}
        latestYear={latestYear}
        threshold={threshold}
        layers={layers}
        health={health.data}
        onMetric={(m) => go({ metric: m })}
        onYear={(y) => go({ year: y === latestYear ? null : y })}
        onThreshold={(t) => go({ threshold: t })}
        onLayers={setLayers}
        onAbout={() => setAbout(true)}
      />
      <main className="layout">
        <section className="map-wrap">
          {geo.data ? (
            <MapView
              regions={geo.data[0]}
              departments={geo.data[1]}
              level={level}
              code={code}
              regionCode={regionCode}
              metric={metric}
              values={values}
              breaks={breaks}
              threshold={threshold}
              lossYears={lossYears}
              layers={layers}
              onSelect={select}
            />
          ) : (
            <p className="loading">Chargement de la carte…</p>
          )}
          <Legend metric={metric} breaks={breaks} />
        </section>

        <aside className="panel" aria-live="polite">
          <nav className="breadcrumb" aria-label="Fil d’Ariane">
            <button type="button" className="link" onClick={() => select('france', 'FR')}>
              France
            </button>
            {level === 'department' && area.data?.parent && (
              <>
                {' › '}
                <button
                  type="button"
                  className="link"
                  onClick={() => select('region', area.data!.parent!.code)}
                >
                  {area.data.parent.name}
                </button>
              </>
            )}
            {level !== 'france' && kpis && <> › {kpis.name}</>}
          </nav>

          {area.error && <p className="error">Zone introuvable ou API indisponible.</p>}
          {kpis && (
            <>
              <h2>{kpis.name}</h2>
              <KpiCards area={kpis} />
            </>
          )}

          {loss.data && (
            <>
              <LossChart series={loss.data.series} />
              <button type="button" className="csv" onClick={exportLoss}>
                Télécharger la perte annuelle (CSV)
              </button>
            </>
          )}
          {alerts.data && (
            <>
              <AlertsChart series={alerts.data.series} />
              <button type="button" className="csv" onClick={exportAlerts}>
                Télécharger les alertes hebdomadaires (CSV)
              </button>
            </>
          )}

          {area.data?.children && area.data.children.length > 0 && (
            <RankingTable
              title={level === 'france' ? 'Régions' : 'Départements'}
              items={area.data.children}
              onSelect={selectChild}
            />
          )}
        </aside>
      </main>
      {about && (
        <AboutPanel meta={meta.data} threshold={threshold} onClose={() => setAbout(false)} />
      )}
    </div>
  )
}
