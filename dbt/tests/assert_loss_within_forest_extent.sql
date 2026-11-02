-- Loss in a year can never exceed the département's 2000 forest extent.
select code, threshold, year, loss_ha, forest_2000_ha
from {{ ref('int_loss__dept_year') }}
where loss_ha > forest_2000_ha
