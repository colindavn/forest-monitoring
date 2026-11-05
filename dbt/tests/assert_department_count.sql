-- Exactly the expected number of départements (96 for metropolitan France).
-- Returns a row (= failure) when the count differs, including when the table is empty.
select count(*) as departments, {{ var('expected_department_count') }} as expected
from {{ ref('stg_admin__departments') }}
having count(*) <> {{ var('expected_department_count') }}
