select
    cast(code as varchar) as code,
    trim(name) as name,
    cast(parent_code as varchar) as country,
    area_km2
from {{ source('raw', 'admin_areas') }}
where admin_level = 1
  and country = '{{ var("country") }}'
