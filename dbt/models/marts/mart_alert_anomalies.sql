-- Weekly alert area compared with a baseline; anomaly when z >= 2.
-- Baseline: the same ISO week of previous years once >= 2 previous years exist
-- ("same_week"); before that, the 12 previous weeks ("rolling_12w"), because GFW only
-- serves DIST-ALERT history from 2025-09-24.
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

same_week as (
    select
        cur.level,
        cur.code,
        cur.threshold,
        cur.week_start,
        count(prev.area_ha_all) as history_years,
        avg(prev.area_ha_all) as mean_ha,
        stddev_samp(prev.area_ha_all) as std_ha
    from weeks as cur
    left join weeks as prev
        on prev.level = cur.level
        and prev.code = cur.code
        and prev.threshold = cur.threshold
        and prev.iso_week = cur.iso_week
        and prev.iso_year < cur.iso_year
    group by all
),

rolling as (
    select
        level,
        code,
        threshold,
        week_start,
        count(area_ha_all) over w as weeks_of_history,
        avg(area_ha_all) over w as mean_ha,
        stddev_samp(area_ha_all) over w as std_ha
    from weeks
    window w as (
        partition by level, code, threshold order by week_start
        rows between 12 preceding and 1 preceding
    )
),

baseline as (
    select
        s.level,
        s.code,
        s.threshold,
        s.week_start,
        s.history_years,
        case
            when s.history_years >= 2 then 'same_week'
            when r.weeks_of_history >= 12 then 'rolling_12w'
        end as baseline_method,
        case
            when s.history_years >= 2 then s.mean_ha
            when r.weeks_of_history >= 12 then r.mean_ha
        end as mean_ha,
        case
            when s.history_years >= 2 then s.std_ha
            when r.weeks_of_history >= 12 then r.std_ha
        end as std_ha
    from same_week as s
    join rolling as r using (level, code, threshold, week_start)
),

scored as (
    select
        w.*,
        b.history_years,
        b.baseline_method,
        b.mean_ha as baseline_mean_ha,
        b.std_ha as baseline_std_ha,
        case when b.std_ha > 0 then (w.area_ha_all - b.mean_ha) / b.std_ha end as z_score
    from weeks as w
    join baseline as b using (level, code, threshold, week_start)
)

select
    *,
    coalesce(z_score >= 2, false) as is_anomaly
from scored
