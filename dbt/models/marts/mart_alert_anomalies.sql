-- Weekly alert area compared with the same ISO week of previous years.
-- z-score only once >= 2 previous years exist; anomaly when z >= 2.
with weeks as (
    select
        level,
        code,
        parent_code,
        threshold,
        week_start,
        isoyear(week_start) as iso_year,
        weekofyear(week_start) as iso_week,
        area_ha_all
    from {{ ref('fct_alerts_week') }}
),

baseline as (
    select
        cur.level,
        cur.code,
        cur.threshold,
        cur.week_start,
        count(prev.area_ha_all) as history_years,
        avg(prev.area_ha_all) as baseline_mean_ha,
        stddev_samp(prev.area_ha_all) as baseline_std_ha
    from weeks as cur
    left join weeks as prev
        on prev.level = cur.level
        and prev.code = cur.code
        and prev.threshold = cur.threshold
        and prev.iso_week = cur.iso_week
        and prev.iso_year < cur.iso_year
    group by all
)

select
    w.level,
    w.code,
    w.parent_code,
    w.threshold,
    w.week_start,
    w.iso_year,
    w.iso_week,
    w.area_ha_all,
    b.history_years,
    b.baseline_mean_ha,
    b.baseline_std_ha,
    case when b.history_years >= 2 and b.baseline_std_ha > 0
        then (w.area_ha_all - b.baseline_mean_ha) / b.baseline_std_ha
    end as z_score,
    coalesce(
        b.history_years >= 2 and b.baseline_std_ha > 0
        and (w.area_ha_all - b.baseline_mean_ha) / b.baseline_std_ha >= 2,
        false
    ) as is_anomaly
from weeks as w
join baseline as b using (level, code, threshold, week_start)
