select
    r.code,
    r.name,
    {{ slugify('r.name') }} as slug,
    r.area_km2,
    sum(e.forest_2000_ha) as forest_2000_ha
from {{ ref('stg_admin__regions') }} as r
left join {{ ref('stg_admin__departments') }} as d on d.region_code = r.code
left join {{ ref('stg_hansen__forest_extent') }} as e
    on e.code = d.code and e.threshold = {{ var('default_threshold') }}
group by all
