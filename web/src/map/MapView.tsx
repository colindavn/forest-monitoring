import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type {
  ExpressionSpecification,
  GeoJSONSource,
  MapLayerMouseEvent,
  MapMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Level, Metric, Threshold } from '../lib/route'
import { formatMetric } from '../lib/labels'
import { NO_DATA_COLOR, colorFor } from '../lib/scale'
import { FRANCE_BOUNDS, boundsOf, type AreaCollection } from './geo'
import { distAlertTiles, hansenLossTiles, ignBasemap, type Basemap } from './tiles'

export interface Layers {
  choropleth: boolean
  hansen: boolean
  alerts: boolean
  alertsHighOnly: boolean
  basemap: Basemap
}

interface Props {
  regions: AreaCollection
  departments: AreaCollection
  level: Level
  code: string
  /** Région shown in département mode (the selected région, or the parent of the département). */
  regionCode: string | null
  metric: Metric
  values: Record<string, number | null>
  breaks: number[]
  threshold: Threshold
  lossYears: [number, number]
  layers: Layers
  onSelect: (level: Level, code: string) => void
}

const ATTRIBUTION =
  '© <a href="https://www.ign.fr/">IGN</a> · Hansen/UMD/Google/USGS/NASA · ' +
  '<a href="https://www.globalforestwatch.org/">Global Forest Watch / WRI</a>'

function colorExpression(values: Record<string, number | null>, breaks: number[]) {
  const entries = Object.entries(values)
  if (entries.length === 0) return NO_DATA_COLOR
  return [
    'match',
    ['get', 'code'],
    ...entries.flatMap(([code, v]) => [code, colorFor(v, breaks)]),
    NO_DATA_COLOR,
  ] as unknown as ExpressionSpecification
}

function rasterSource(tiles: string, attribution?: string): maplibregl.RasterSourceSpecification {
  return { type: 'raster', tiles: [tiles], tileSize: 256, attribution }
}

export default function MapView(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)
  // Latest props for event handlers registered once.
  const latest = useRef(props)
  useEffect(() => {
    latest.current = props
  })

  // Create the map once.
  useEffect(() => {
    if (!container.current) return
    const map = new maplibregl.Map({
      container: container.current,
      bounds: FRANCE_BOUNDS,
      attributionControl: { compact: true, customAttribution: ATTRIBUTION },
      style: {
        version: 8,
        sources: {
          plan: rasterSource(ignBasemap('plan')),
          ortho: rasterSource(ignBasemap('ortho')),
        },
        layers: [
          { id: 'plan', type: 'raster', source: 'plan' },
          { id: 'ortho', type: 'raster', source: 'ortho', layout: { visibility: 'none' } },
        ],
      },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    mapRef.current = map

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
    const hover = (e: MapLayerMouseEvent) => {
      const f = e.features?.[0]
      if (!f) return
      map.getCanvas().style.cursor = 'pointer'
      const { code, name } = f.properties as { code: string; name: string }
      const { values, metric } = latest.current
      const value = values[code]
      const ranked = Object.entries(values)
        .filter(([, v]) => v != null)
        .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
      const rank = ranked.findIndex(([c]) => c === code) + 1
      const html = document.createElement('div')
      html.className = 'tooltip'
      const title = document.createElement('strong')
      title.textContent = `${name} (${code})`
      const body = document.createElement('div')
      body.textContent =
        code in values
          ? `${formatMetric(metric, value)}${rank ? ` · rang ${rank}/${ranked.length}` : ''}`
          : ''
      html.append(title, body)
      popup.setLngLat(e.lngLat).setDOMContent(html).addTo(map)
    }
    const leave = () => {
      map.getCanvas().style.cursor = ''
      popup.remove()
    }

    map.on('load', () => {
      const { regions, departments } = latest.current
      map.addSource('regions', { type: 'geojson', data: regions, promoteId: 'code' })
      map.addSource('departments', { type: 'geojson', data: departments, promoteId: 'code' })
      map.addLayer({
        id: 'regions-fill',
        type: 'fill',
        source: 'regions',
        paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.75 },
      })
      map.addLayer({
        id: 'departments-fill',
        type: 'fill',
        source: 'departments',
        paint: { 'fill-color': NO_DATA_COLOR, 'fill-opacity': 0.75 },
        filter: ['==', ['get', 'parent_code'], ''],
      })
      map.addLayer({
        id: 'departments-line',
        type: 'line',
        source: 'departments',
        paint: { 'line-color': '#5b5b5b', 'line-width': 0.6 },
        filter: ['==', ['get', 'parent_code'], ''],
      })
      map.addLayer({
        id: 'regions-line',
        type: 'line',
        source: 'regions',
        paint: { 'line-color': '#333', 'line-width': 1.2 },
      })
      map.addLayer({
        id: 'selected-line',
        type: 'line',
        source: 'departments',
        paint: { 'line-color': '#0b3d91', 'line-width': 3 },
        filter: ['==', ['get', 'code'], ''],
      })

      for (const layer of ['regions-fill', 'departments-fill']) {
        map.on('mousemove', layer, hover)
        map.on('mouseleave', layer, leave)
      }
      map.on('click', (e: MapMouseEvent) => {
        const hits = map.queryRenderedFeatures(e.point, {
          layers: ['departments-fill', 'regions-fill'],
        })
        const hit = hits[0]
        if (!hit) return
        const code = (hit.properties as { code: string }).code
        latest.current.onSelect(hit.layer.id === 'departments-fill' ? 'department' : 'region', code)
      })
      setReady(true)
    })
    return () => {
      popup.remove()
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Choropleth colours, filters and selection.
  const { level, code, regionCode, values, breaks, layers } = props
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const colors = colorExpression(values, breaks)
    const inRegion: maplibregl.FilterSpecification = [
      '==',
      ['get', 'parent_code'],
      regionCode ?? '',
    ]
    const show = layers.choropleth ? 'visible' : 'none'

    if (level === 'france') {
      map.setPaintProperty('regions-fill', 'fill-color', colors)
      map.setPaintProperty('regions-fill', 'fill-opacity', 0.75)
    } else {
      // Dim the other régions; the selected one is drawn by its départements.
      map.setPaintProperty('regions-fill', 'fill-color', [
        'case',
        ['==', ['get', 'code'], regionCode ?? ''],
        'rgba(0,0,0,0)',
        '#bdbdbd',
      ])
      map.setPaintProperty('regions-fill', 'fill-opacity', 0.55)
      map.setPaintProperty('departments-fill', 'fill-color', colors)
    }
    map.setFilter('departments-fill', level === 'france' ? ['==', 'x', 'y'] : inRegion)
    map.setFilter('departments-line', level === 'france' ? ['==', 'x', 'y'] : inRegion)
    map.setFilter('selected-line', ['==', ['get', 'code'], level === 'department' ? code : ''])
    map.setLayoutProperty('regions-fill', 'visibility', show)
    map.setLayoutProperty('departments-fill', 'visibility', show)
  }, [ready, level, code, regionCode, values, breaks, layers.choropleth])

  // Zoom to the selection.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const bounds =
      level === 'france'
        ? FRANCE_BOUNDS
        : level === 'region'
          ? boundsOf(props.regions, (p) => p.code === code)
          : boundsOf(props.departments, (p) => p.code === code)
    if (bounds) map.fitBounds(bounds, { padding: 40, duration: 800 })
  }, [ready, level, code, props.regions, props.departments])

  // Basemap and raster overlays.
  const { threshold, lossYears } = props
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    map.setLayoutProperty('plan', 'visibility', layers.basemap === 'plan' ? 'visible' : 'none')
    map.setLayoutProperty('ortho', 'visibility', layers.basemap === 'ortho' ? 'visible' : 'none')

    const overlays: [string, boolean, string][] = [
      [
        'hansen',
        layers.hansen,
        hansenLossTiles({ startYear: lossYears[0], endYear: lossYears[1], threshold }),
      ],
      [
        'alerts',
        layers.alerts,
        distAlertTiles({ today: new Date(), threshold, highConfidenceOnly: layers.alertsHighOnly }),
      ],
    ]
    for (const [id, visible, tiles] of overlays) {
      const existing = map.getSource(id) as maplibregl.RasterTileSource | undefined
      if (!visible) {
        if (map.getLayer(id)) map.removeLayer(id)
        if (existing) map.removeSource(id)
        continue
      }
      if (existing) existing.setTiles([tiles])
      else {
        map.addSource(id, rasterSource(tiles))
        map.addLayer({ id, type: 'raster', source: id }, 'departments-line')
      }
    }
  }, [ready, layers, threshold, lossYears])

  // Keep sources in sync if geometry props change (they normally don't).
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    ;(map.getSource('regions') as GeoJSONSource).setData(props.regions)
    ;(map.getSource('departments') as GeoJSONSource).setData(props.departments)
  }, [ready, props.regions, props.departments])

  return <div ref={container} className="map" role="region" aria-label="Carte de la perte" />
}
