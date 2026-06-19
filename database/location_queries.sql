-- =============================================================================
-- location_queries.sql
-- TransitAI — Useful SQL Queries for the Locations Table
-- =============================================================================


-- =============================================================================
-- 1. List ALL locations (sorted by State → City → Name)
-- =============================================================================
SELECT
    id,
    name,
    city,
    state,
    latitude,
    longitude,
    type
FROM locations
ORDER BY state, city, name;


-- =============================================================================
-- 2. List locations by a specific STATE
--    Replace 'Kerala' with the desired state name.
-- =============================================================================
SELECT
    id,
    name,
    city,
    state,
    latitude,
    longitude,
    type
FROM locations
WHERE state = 'Kerala'
ORDER BY city, name;


-- =============================================================================
-- 3. List locations by a specific CITY
--    Replace 'Kochi' with the desired city name.
-- =============================================================================
SELECT
    id,
    name,
    city,
    state,
    latitude,
    longitude,
    type
FROM locations
WHERE city = 'Kochi'
ORDER BY name;


-- =============================================================================
-- 4. Count locations per STATE
-- =============================================================================
SELECT
    state,
    COUNT(*) AS location_count
FROM locations
GROUP BY state
ORDER BY location_count DESC, state;


-- =============================================================================
-- 5. Count locations per CITY
-- =============================================================================
SELECT
    city,
    state,
    COUNT(*) AS location_count
FROM locations
GROUP BY city, state
ORDER BY location_count DESC, state, city;


-- =============================================================================
-- 6. Count locations per TYPE (metro_station, railway_station, bus_stop, etc.)
-- =============================================================================
SELECT
    type,
    COUNT(*) AS location_count
FROM locations
GROUP BY type
ORDER BY location_count DESC;


-- =============================================================================
-- 7. Detect DUPLICATE entries (same name + city + state appearing more than once)
-- =============================================================================
SELECT
    name,
    city,
    state,
    COUNT(*) AS occurrences
FROM locations
GROUP BY
    LOWER(TRIM(name)),
    LOWER(TRIM(city)),
    LOWER(TRIM(state))
HAVING COUNT(*) > 1
ORDER BY occurrences DESC, state, city, name;


-- =============================================================================
-- 8. Locations with MISSING coordinates (latitude or longitude is NULL)
-- =============================================================================
SELECT
    id,
    name,
    city,
    state,
    type
FROM locations
WHERE latitude IS NULL OR longitude IS NULL
ORDER BY state, city, name;


-- =============================================================================
-- 9. States covered (distinct states in the database)
-- =============================================================================
SELECT DISTINCT state
FROM locations
ORDER BY state;


-- =============================================================================
-- 10. Cities covered (distinct cities with their state)
-- =============================================================================
SELECT DISTINCT
    city,
    state
FROM locations
ORDER BY state, city;


-- =============================================================================
-- 11. Locations that have NO associated transit routes (isolated stops)
--     Useful for data-quality auditing.
-- =============================================================================
SELECT
    l.id,
    l.name,
    l.city,
    l.state,
    l.type
FROM locations l
WHERE l.id NOT IN (
    SELECT DISTINCT source_location_id FROM routes
    WHERE transport_mode != 'walk'
    UNION
    SELECT DISTINCT destination_location_id FROM routes
    WHERE transport_mode != 'walk'
)
ORDER BY l.state, l.city, l.name;


-- =============================================================================
-- 12. Full location detail joined with route count
--     Shows how many transit routes are connected to each location.
-- =============================================================================
SELECT
    l.id,
    l.name,
    l.city,
    l.state,
    l.type,
    l.latitude,
    l.longitude,
    COUNT(r.id) AS connected_routes
FROM locations l
LEFT JOIN routes r
    ON (r.source_location_id = l.id OR r.destination_location_id = l.id)
    AND r.transport_mode != 'walk'
GROUP BY l.id
ORDER BY l.state, l.city, l.name;
