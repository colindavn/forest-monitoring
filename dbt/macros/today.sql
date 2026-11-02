{# Reference "today" as a SQL date; overridable with --vars "{today: '2025-02-28'}" in tests. #}
{% macro today() -%}
    {%- if var('today') -%}date '{{ var("today") }}'{%- else -%}current_date{%- endif -%}
{%- endmacro %}
