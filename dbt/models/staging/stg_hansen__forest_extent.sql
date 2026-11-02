select
    cast(code as varchar) as code,
    threshold,
    forest_2000_ha,
    _source_version as source_version
from {{ source('raw', 'hansen_forest_extent') }}
where country = '{{ var("country") }}'
