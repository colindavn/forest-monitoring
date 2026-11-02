-- One row per level × area × threshold with the headline numbers shown in the KPI cards.
with loss as (
    select *, max(year) over () as latest_year
    from {{ ref('fct_loss_year') }}
),

loss_kpis as (
    select
        level,
        code,
        parent_code,
        threshold,
        any_value(latest_year) as latest_year,
        any_value(forest_2000_ha) as forest_2000_ha,
        sum(loss_ha) filter (where year = latest_year) as loss_latest_ha,
        sum(loss_ha_5y_avg) filter (where year = latest_year) as loss_5y_avg_ha,
        sum(loss_ha) as loss_total_ha,
        regr_slope(loss_ha, year) filter (where year > latest_year - 10) as trend_slope_ha_per_year
    from loss
    group by level, code, parent_code, threshold
),

alerts as (
    select *, max(week_start) over () as latest_week
    from {{ ref('fct_alerts_week') }}
),

alert_kpis as (
    select level, code, threshold, area_ha_4w_rolling as alerts_last_4w_ha, latest_week
    from alerts
    where week_start = latest_week
),

names as (
    select 'region' as level, code, name from {{ ref('stg_admin__regions') }}
    union all
    select 'department', code, name from {{ ref('stg_admin__departments') }}
    union all
    select 'france', '{{ var("country") }}', 'France'
)

select
    l.level,
    l.code,
    n.name,
    l.parent_code,
    l.threshold,
    l.forest_2000_ha,
    l.latest_year,
    l.loss_latest_ha,
    l.loss_latest_ha / nullif(l.forest_2000_ha, 0) as loss_latest_pct,
    l.loss_5y_avg_ha,
    l.loss_total_ha,
    l.loss_total_ha / nullif(l.forest_2000_ha, 0) as loss_total_pct,
    coalesce(l.trend_slope_ha_per_year, 0) as trend_slope_ha_per_year,
    coalesce(a.alerts_last_4w_ha, 0) as alerts_last_4w_ha,
    a.latest_week as latest_alert_week,
    case when l.parent_code is not null then
        rank() over (partition by l.level, l.parent_code, l.threshold order by l.loss_latest_ha desc)
    end as rank_in_parent
from loss_kpis as l
left join names as n using (level, code)
left join alert_kpis as a using (level, code, threshold)
