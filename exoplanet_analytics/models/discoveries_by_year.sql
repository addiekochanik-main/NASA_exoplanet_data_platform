SELECT
    disc_year,
    COUNT(*) AS total_discoveries
FROM public.raw_exoplanets
WHERE disc_year IS NOT NULL
GROUP BY disc_year