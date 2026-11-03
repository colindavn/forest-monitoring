import { useMemo, useState } from 'react'
import type { AreaKpis } from '../api/client'
import { formatHa, formatPct } from '../lib/format'
import { formatMetric } from '../lib/labels'

type SortKey = 'name' | 'loss_latest_ha' | 'loss_total_pct' | 'alerts_last_4w_ha' | 'trend'

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: 'name', label: 'Nom' },
  { key: 'loss_latest_ha', label: 'Perte dernière année' },
  { key: 'loss_total_pct', label: 'Perte totale (% 2000)' },
  { key: 'alerts_last_4w_ha', label: 'Alertes 4 sem.' },
  { key: 'trend', label: 'Tendance' },
]

function sortValue(a: AreaKpis, key: SortKey): number | string {
  if (key === 'name') return a.name
  if (key === 'trend') return a.trend_slope_ha_per_year
  return a[key] ?? -Infinity
}

interface Props {
  title: string
  items: AreaKpis[]
  onSelect: (item: AreaKpis) => void
}

export default function RankingTable({ title, items, onSelect }: Props) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({
    key: 'loss_latest_ha',
    desc: true,
  })
  const sorted = useMemo(() => {
    const out = [...items].sort((a, b) => {
      const va = sortValue(a, sort.key)
      const vb = sortValue(b, sort.key)
      const cmp = typeof va === 'string' ? va.localeCompare(String(vb), 'fr') : va - (vb as number)
      return sort.desc ? -cmp : cmp
    })
    return out
  }, [items, sort])

  return (
    <section className="ranking">
      <h3>{title}</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={sort.key === c.key ? (sort.desc ? 'descending' : 'ascending') : 'none'}
                >
                  <button
                    type="button"
                    className="sort"
                    onClick={() =>
                      setSort((s) => ({ key: c.key, desc: s.key === c.key ? !s.desc : true }))
                    }
                  >
                    {c.label}
                    {sort.key === c.key ? (sort.desc ? ' ▼' : ' ▲') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((a) => (
              <tr key={a.code}>
                <th scope="row">
                  <button type="button" className="link" onClick={() => onSelect(a)}>
                    {a.name} <span className="code">({a.code})</span>
                  </button>
                </th>
                <td>{formatHa(a.loss_latest_ha)}</td>
                <td>{formatPct(a.loss_total_pct)}</td>
                <td>{formatHa(a.alerts_last_4w_ha)}</td>
                <td>{formatMetric('trend_slope', a.trend_slope_ha_per_year)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
