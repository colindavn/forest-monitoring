select
    cast(code as varchar) as code,
    threshold,
    alert_date,
    confidence_code,
    case confidence_code
        when 2 then 'nominal'
        when 3 then 'high'
        when 4 then 'highest'
    end as confidence,
    area_ha,
    _source_version as source_version
from {{ source('raw', 'dist_alerts_day') }}
where country = '{{ var("country") }}'
  and alert_date >= date '{{ var("alerts_start_date") }}'
