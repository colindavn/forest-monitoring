-- Département × threshold × ISO week (Monday start), zero-filled over the full week range
-- so rolling windows and anomaly baselines see every week.
with alerts as (
    select *, cast(date_trunc('week', alert_date) as date) as week_start
    from {{ ref('stg_gfw__dist_alerts') }}
),

weeks as (
    select cast(unnest(generate_series(
        (select min(week_start) from alerts),
        (select max(week_start) from alerts),
        interval 7 day
    )) as date) as week_start
),

thresholds as (
    select unnest({{ var('thresholds') }}) as threshold
),

spine as (
    select d.code, t.threshold, w.week_start
    from {{ ref('stg_admin__departments') }} as d
    cross join thresholds as t
    cross join weeks as w
),

weekly as (
    select
        code,
        threshold,
        week_start,
        sum(area_ha) filter (where confidence = 'nominal') as area_ha_nominal,
        sum(area_ha) filter (where confidence = 'high') as area_ha_high,
        sum(area_ha) filter (where confidence = 'highest') as area_ha_highest
    from alerts
    group by all
)

select
    s.code,
    s.threshold,
    s.week_start,
    coalesce(w.area_ha_nominal, 0) as area_ha_nominal,
    coalesce(w.area_ha_high, 0) as area_ha_high,
    coalesce(w.area_ha_highest, 0) as area_ha_highest,
    coalesce(w.area_ha_high, 0) + coalesce(w.area_ha_highest, 0) as area_ha_high_conf,
    coalesce(w.area_ha_nominal, 0) + coalesce(w.area_ha_high, 0)
        + coalesce(w.area_ha_highest, 0) as area_ha_all
from spine as s
left join weekly as w using (code, threshold, week_start)
