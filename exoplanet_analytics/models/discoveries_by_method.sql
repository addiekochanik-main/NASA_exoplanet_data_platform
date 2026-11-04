SELECT
    discoverymethod,
    COUNT(*) AS total_planets
FROM public.raw_exoplanets
WHERE discoverymethod IS NOT NULL
GROUP BY discoverymethod