CREATE OR REPLACE FUNCTION public._final_median(numeric[])
   RETURNS numeric AS
$$
   SELECT AVG(val)
   FROM (
     SELECT val
     FROM unnest($1) val
     ORDER BY 1
     LIMIT  2 - MOD(array_upper($1, 1), 2)
     OFFSET CEIL(array_upper($1, 1) / 2.0) - 1
   ) sub;
$$
LANGUAGE 'sql' IMMUTABLE;

CREATE AGGREGATE public.median(numeric) (
  SFUNC=array_append,
  STYPE=numeric[],
  FINALFUNC=public._final_median,
  INITCOND='{}'
);