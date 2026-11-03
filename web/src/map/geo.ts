import type { FeatureCollection, Geometry, Position } from 'geojson'

export interface AreaProps {
  code: string
  name: string
  parent_code: string
}

export type AreaCollection = FeatureCollection<Geometry, AreaProps>
export type Bounds = [[number, number], [number, number]]

export const FRANCE_BOUNDS: Bounds = [
  [-5.3, 41.3],
  [9.7, 51.2],
]

function* positions(geometry: Geometry): Generator<Position> {
  switch (geometry.type) {
    case 'Polygon':
      for (const ring of geometry.coordinates) yield* ring
      break
    case 'MultiPolygon':
      for (const poly of geometry.coordinates) for (const ring of poly) yield* ring
      break
    default:
      break
  }
}

/** Bounding box of the features matching `predicate`. */
export function boundsOf(fc: AreaCollection, predicate: (p: AreaProps) => boolean): Bounds | null {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const f of fc.features) {
    if (!predicate(f.properties)) continue
    for (const [x, y] of positions(f.geometry)) {
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  }
  return Number.isFinite(minX)
    ? [
        [minX, minY],
        [maxX, maxY],
      ]
    : null
}

export async function loadGeo(name: 'regions' | 'departments'): Promise<AreaCollection> {
  const resp = await fetch(`/geo/${name}.geojson`)
  if (!resp.ok) throw new Error(`Cannot load ${name}.geojson`)
  return (await resp.json()) as AreaCollection
}
