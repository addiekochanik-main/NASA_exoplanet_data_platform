-- Exoplanet discoveries by year
CREATE OR REPLACE VIEW discoveries_by_year AS
SELECT
    disc_year,
    COUNT(*) AS total_discoveries
FROM raw_exoplanets
WHERE disc_year IS NOT NULL
GROUP BY disc_year;


-- Exoplanets by discovery method
CREATE OR REPLACE VIEW discoveries_by_method AS
SELECT
    discoverymethod,
    COUNT(*) AS total_planets
FROM raw_exoplanets
WHERE discoverymethod IS NOT NULL
GROUP BY discoverymethod;


-- Planet characteristics by discovery method
CREATE OR REPLACE VIEW planet_characteristics AS
SELECT
    discoverymethod,
    COUNT(*) AS total_planets,
    ROUND(AVG(pl_rade)::numeric, 2) AS avg_radius_earth,
    ROUND(AVG(pl_orbper)::numeric, 2) AS avg_orbital_period_days
FROM raw_exoplanets
WHERE discoverymethod IS NOT NULL
GROUP BY discoverymethod;