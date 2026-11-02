select
    d.code,
    d.name,
    {{ slugify('d.name') }} as slug,
    d.region_code,
    d.area_km2,
    e.forest_2000_ha
from {{ ref('stg_admin__departments') }} as d
left join {{ ref('stg_hansen__forest_extent') }} as e
    on e.code = d.code and e.threshold = {{ var('default_threshold') }}
