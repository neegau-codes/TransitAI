-- Schema for TransitAI Database

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL UNIQUE,
    transport_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_location_id INTEGER NOT NULL,
    destination_location_id INTEGER NOT NULL,
    transport_mode TEXT NOT NULL, -- 'metro', 'train', 'bus', 'walk'
    provider TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    cost REAL NOT NULL,
    distance_km REAL,
    route_name TEXT NOT NULL,
    FOREIGN KEY (source_location_id) REFERENCES locations(id),
    FOREIGN KEY (destination_location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    departure_time TEXT NOT NULL, -- HH:MM format
    arrival_time TEXT NOT NULL,   -- HH:MM format
    FOREIGN KEY (route_id) REFERENCES routes(id)
);
