SELECT
    discoverymethod,
    COUNT(*) AS total_planets,
    ROUND(AVG(pl_rade)::numeric, 2) AS avg_radius_earth,
    ROUND(AVG(pl_orbper)::numeric, 2) AS avg_orbital_period_days
FROM public.raw_exoplanets
WHERE discoverymethod IS NOT NULL
GROUP BY discoverymethod