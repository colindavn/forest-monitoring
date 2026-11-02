-- Drill-down consistency: each région row equals the sum of its départements, and France
-- equals the sum of régions.
with dept as (
    select parent_code as code, threshold, year, sum(loss_ha) as loss_ha
    from {{ ref('fct_loss_year') }}
    where level = 'department'
    group by all
),

region as (
    select code, threshold, year, loss_ha
    from {{ ref('fct_loss_year') }}
    where level = 'region'
),

country as (
    select threshold, year, loss_ha
    from {{ ref('fct_loss_year') }}
    where level = 'france'
),

region_sum as (
    select threshold, year, sum(loss_ha) as loss_ha from region group by all
)

select 'region' as check_level, r.code, r.threshold, r.year
from region as r
full join dept as d using (code, threshold, year)
where abs(coalesce(r.loss_ha, 0) - coalesce(d.loss_ha, 0)) > 1e-6

union all

select 'france', null, c.threshold, c.year
from country as c
full join region_sum as s using (threshold, year)
where abs(coalesce(c.loss_ha, 0) - coalesce(s.loss_ha, 0)) > 1e-6
