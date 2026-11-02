{# URL-friendly slug: "Provence-Alpes-Côte d'Azur" → "provence-alpes-cote-d-azur". #}
{% macro slugify(expr) -%}
    trim(regexp_replace(lower(strip_accents({{ expr }})), '[^a-z0-9]+', '-', 'g'), '-')
{%- endmacro %}
