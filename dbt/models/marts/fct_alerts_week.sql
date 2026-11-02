-- Weekly DIST-ALERT area for every level; région and France rows are sums of départements.
with dept as (
    select
        'department' as level,
        a.code,
        d.region_code as parent_code,
        a.* exclude (code)
    from {{ ref('int_alerts__dept_week') }} as a
    join {{ ref('stg_admin__departments') }} as d using (code)
),

{% set measures = ['area_ha_nominal', 'area_ha_high', 'area_ha_highest', 'area_ha_high_conf', 'area_ha_all'] %}

region as (
    select
        'region' as level,
        parent_code as code,
        '{{ var("country") }}' as parent_code,
        threshold,
        week_start,
        {% for m in measures %}sum({{ m }}) as {{ m }}{{ "," if not loop.last }}
        {% endfor %}
    from dept
    group by all
),

country as (
    select
        'france' as level,
        '{{ var("country") }}' as code,
        null as parent_code,
        threshold,
        week_start,
        {% for m in measures %}sum({{ m }}) as {{ m }}{{ "," if not loop.last }}
        {% endfor %}
    from dept
    group by all
),

unioned as (
    select * from dept
    union all by name select * from region
    union all by name select * from country
)

select
    level,
    code,
    parent_code,
    threshold,
    week_start,
    {% for m in measures %}{{ m }},
    {% endfor %}
    sum(area_ha_all) over (
        partition by level, code, threshold order by week_start
        rows between 3 preceding and current row
    ) as area_ha_4w_rolling
from unioned
