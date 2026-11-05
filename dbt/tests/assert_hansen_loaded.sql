-- Hansen forest extent and loss must be loaded for every forest threshold.
with expected as (
    select unnest({{ var('thresholds') }}) as threshold
)

select e.threshold
from expected as e
where not exists (
    select 1 from {{ ref('stg_hansen__forest_extent') }} as f where f.threshold = e.threshold
)
or not exists (
    select 1 from {{ ref('stg_hansen__loss') }} as l where l.threshold = e.threshold
)
