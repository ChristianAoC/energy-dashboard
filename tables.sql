BEGIN;

CREATE TABLE building (
	id VARCHAR(20) NOT NULL,
	name VARCHAR(75) NOT NULL,
	floor_area INTEGER,
	year_built INTEGER,
	occupancy_type VARCHAR(20) NOT NULL CHECK (occupancy_type IN ('sport', 'lecture theatre', 'library', 'catering', 'administration', 'academic bio', 'academic arts', 'academic physics', 'academic engineering', 'academic other', 'Residential', 'Non Res', 'Split Use')),
	maze_map_label JSON,
	PRIMARY KEY (id),
	UNIQUE (name)
);

CREATE TABLE cache_meta (
	meta_type VARCHAR NOT NULL,
	to_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	from_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	processing_time FLOAT NOT NULL,
	offline BOOLEAN NOT NULL,
	PRIMARY KEY (meta_type)
);

CREATE TABLE "user" (
	email VARCHAR(254) NOT NULL,
	level INTEGER NOT NULL,
	login_count INTEGER NOT NULL,
	last_login TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (email)
);

CREATE TABLE settings (
	key VARCHAR NOT NULL,
	value JSON,
	setting_type VARCHAR NOT NULL,
	PRIMARY KEY (key)
);

CREATE TABLE log (
	id SERIAL NOT NULL,
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	message VARCHAR NOT NULL,
	info VARCHAR,
	level VARCHAR NOT NULL CHECK (level IN ('info', 'warning', 'error', 'critical')),
	PRIMARY KEY (id)
);

CREATE TABLE meter (
	id VARCHAR(30) NOT NULL,
	"SEED_uuid" VARCHAR(36),
	description VARCHAR NOT NULL,
	main BOOLEAN NOT NULL,
	utility_type VARCHAR(11) NOT NULL CHECK (utility_type IN ('gas', 'electricity', 'heat', 'water', 'weather')),
	reading_type VARCHAR(10) NOT NULL CHECK (reading_type IN ('cumulative', 'rate')),
	units VARCHAR(5) NOT NULL,
	resolution FLOAT,
	scaling_factor FLOAT NOT NULL,
	invoiced BOOLEAN NOT NULL,
	building_id VARCHAR,
	PRIMARY KEY (id),
	UNIQUE ("SEED_uuid"),
	FOREIGN KEY(building_id) REFERENCES building (id) ON DELETE CASCADE
);

CREATE TABLE utility_data (
	building_id VARCHAR NOT NULL,
	electricity JSON,
	gas JSON,
	heat JSON,
	water JSON,
	PRIMARY KEY (building_id),
	FOREIGN KEY(building_id) REFERENCES building (id) ON DELETE CASCADE
);

CREATE TABLE sessions (
	id VARCHAR NOT NULL,
	email VARCHAR(254) NOT NULL,
	last_seen TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id, email),
	FOREIGN KEY(email) REFERENCES "user" (email) ON DELETE CASCADE
);

CREATE TABLE login_code (
	email VARCHAR(254) NOT NULL,
	code VARCHAR(6) NOT NULL,
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (email, code, timestamp),
	FOREIGN KEY(email) REFERENCES "user" (email) ON DELETE CASCADE
);

CREATE TABLE context (
	id SERIAL NOT NULL,
	author VARCHAR(254) NOT NULL,
	target_type VARCHAR(8) NOT NULL CHECK (target_type IN ('building', 'meter')),
	target_id VARCHAR NOT NULL,
	start_timestamp TIMESTAMP WITHOUT TIME ZONE,
	end_timestamp TIMESTAMP WITHOUT TIME ZONE,
	context_type VARCHAR NOT NULL,
	comment VARCHAR NOT NULL,
	deleted BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(author) REFERENCES "user" (email) ON DELETE CASCADE
);

CREATE TABLE health_check (
	meter_id VARCHAR NOT NULL,
	count INTEGER,
	count_perc VARCHAR(6),
	count_score INTEGER,
	zeroes INTEGER,
	zeroes_perc VARCHAR(6),
	zeroes_score INTEGER,
	diff_neg INTEGER,
	diff_neg_perc VARCHAR(6),
	diff_pos INTEGER,
	diff_pos_perc VARCHAR(6),
	diff_pos_score INTEGER,
	diff_zero INTEGER,
	diff_zero_perc VARCHAR(6),
	class_check VARCHAR(28),
	functional_matrix INTEGER,
	mean INTEGER,
	median INTEGER,
	mode INTEGER,
	std INTEGER,
	min_value INTEGER,
	max_value INTEGER,
	outliers INTEGER,
	score INTEGER,
	outliers_perc VARCHAR(6),
	outliers_ignz INTEGER,
	outliers_ignz_perc VARCHAR(6),
	PRIMARY KEY (meter_id),
	FOREIGN KEY(meter_id) REFERENCES meter (id) ON DELETE CASCADE
);

COMMIT;