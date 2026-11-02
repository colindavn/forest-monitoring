with src as (
    select * from {{ source('raw', 'hansen_loss') }}
    where country = '{{ var("country") }}'
)

select
    cast(code as varchar) as code,
    threshold,
    year,
    loss_ha,
    _source_version as source_version
from src
where year between {{ var('first_loss_year') }} and (select max(year) from src)
  and loss_ha >= 0
