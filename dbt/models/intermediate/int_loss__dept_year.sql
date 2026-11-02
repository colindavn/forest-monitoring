-- Département × threshold × year, zero-filled from first_loss_year to the latest loss year.
with years as (
    select unnest(range(
        {{ var('first_loss_year') }},
        (select max(year) from {{ ref('stg_hansen__loss') }}) + 1
    )) as year
),

spine as (
    select e.code, e.threshold, e.forest_2000_ha, y.year
    from {{ ref('stg_hansen__forest_extent') }} as e
    cross join years as y
)

select
    s.code,
    s.threshold,
    s.year,
    s.forest_2000_ha,
    coalesce(l.loss_ha, 0) as loss_ha
from spine as s
left join {{ ref('stg_hansen__loss') }} as l
    on l.code = s.code and l.threshold = s.threshold and l.year = s.year
