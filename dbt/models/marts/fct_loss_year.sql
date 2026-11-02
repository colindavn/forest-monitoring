-- Annual loss for every level. Région and France rows are sums of département rows
-- (never recomputed from rasters) so drill-down totals always add up.
with dept as (
    select
        'department' as level,
        l.code,
        d.region_code as parent_code,
        l.threshold,
        l.year,
        l.forest_2000_ha,
        l.loss_ha
    from {{ ref('int_loss__dept_year') }} as l
    join {{ ref('stg_admin__departments') }} as d using (code)
),

region as (
    select
        'region' as level,
        parent_code as code,
        '{{ var("country") }}' as parent_code,
        threshold,
        year,
        sum(forest_2000_ha) as forest_2000_ha,
        sum(loss_ha) as loss_ha
    from dept
    group by all
),

country as (
    select
        'france' as level,
        '{{ var("country") }}' as code,
        null as parent_code,
        threshold,
        year,
        sum(forest_2000_ha) as forest_2000_ha,
        sum(loss_ha) as loss_ha
    from dept
    group by all
),

unioned as (
    select * from dept
    union all by name select * from region
    union all by name select * from country
)

select
    level,
    code,
    parent_code,
    threshold,
    year,
    forest_2000_ha,
    loss_ha,
    loss_ha / nullif(forest_2000_ha, 0) as loss_pct_of_2000,
    sum(loss_ha) over w_cum as cum_loss_ha,
    avg(loss_ha) over (w_ord rows between 4 preceding and current row) as loss_ha_5y_avg,
    (loss_ha - lag(loss_ha) over w_ord) / nullif(lag(loss_ha) over w_ord, 0) as yoy_change_pct
from unioned
window
    w_ord as (partition by level, code, threshold order by year),
    w_cum as (partition by level, code, threshold order by year rows unbounded preceding)
