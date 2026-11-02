select
    cast(code as varchar) as code,
    trim(name) as name,
    cast(parent_code as varchar) as region_code,
    area_km2
from {{ source('raw', 'admin_areas') }}
where admin_level = 2
  and country = '{{ var("country") }}'
