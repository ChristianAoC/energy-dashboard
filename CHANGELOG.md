# Changelog
## Pre-Release
This list contains the breaking changes for individual commits (anything that needs to be manually changed on the server).

### Commit [7871ff3884b5f9de7e6b193c9fc3aaf604134ea7](https://github.com/ChristianAoC/energy-dashboard/commit/7871ff3884b5f9de7e6b193c9fc3aaf604134ea7)
### Created settings:
- server.session_timeout
- server.login_code_timeout
- server.log_info_expiry
- server.log_warning_expiry
- server.log_error_expiry
- server.log_critical_expiry

```sql
BEGIN TRANSACTION;

INSERT INTO settings (key, category, value, setting_type) VALUES
    ('session_timeout', 'server', '365', 'int'),
    ('login_code_timeout', 'server', '60', 'int'),
    ('log_info_expiry', 'server', '7', 'int'),
    ('log_warning_expiry', 'server', '14', 'int'),
    ('log_error_expiry', 'server', '30', 'int'),
    ('log_critical_expiry', 'server', '180', 'int');

COMMIT;
```

### Commit [91eef74579f72a6eeca6e6938c9c5db5b0aedaa6](https://github.com/ChristianAoC/energy-dashboard/commit/91eef74579f72a6eeca6e6938c9c5db5b0aedaa6)
#### Recategorised settings:
- data.BACKGROUND_TASK_TIMING => server.BACKGROUND_TASK_TIMING

```sql
BEGIN TRANSACTION;

UPDATE settings
SET category = 'server'
WHERE key = 'BACKGROUND_TASK_TIMING' AND category = 'data';

COMMIT;
```

#### Altered table:
Settings table primary key changed "key" to "key and category".

```sql
BEGIN TRANSACTION;

ALTER TABLE settings DROP PRIMARY KEY;
ALTER TABLE settings ADD PRIMARY KEY (key, category);

COMMIT;
```

### Commit [06d24ab648df237aed04d566d084b091cc28d4e7](https://github.com/ChristianAoC/energy-dashboard/commit/06d24ab648df237aed04d566d084b091cc28d4e7)
#### Recategorised settings:
- metadata.meter_sheet => metadata.meter_sheet.meter_sheet
- metadata.building_sheet => metadata.building_sheet.building_sheet

```sql
BEGIN TRANSACTION;

UPDATE settings
SET category = 'metadata.meter_sheet'
WHERE key = 'meter_sheet' AND category = 'metadata';

UPDATE settings
SET category = 'metadata.building_sheet'
WHERE key = 'building_sheet' AND category = 'metadata';

COMMIT;
```

#### Created settings:
- metadata.meter_sheet.meter_id
- metadata.meter_sheet.raw_uuid
- metadata.meter_sheet.description
- metadata.meter_sheet.building_level_meter
- metadata.meter_sheet.meter_type
- metadata.meter_sheet.reading_type
- metadata.meter_sheet.units
- metadata.meter_sheet.resolution
- metadata.meter_sheet.unit_conversion_factor
- metadata.meter_sheet.tenant
- metadata.meter_sheet.meter_building
- metadata.building_sheet.building_code
- metadata.building_sheet.building_name
- metadata.building_sheet.floor_area
- metadata.building_sheet.year_built
- metadata.building_sheet.usage
- metadata.building_sheet.maze_map_label

```sql
BEGIN TRANSACTION;

INSERT INTO settings (key, category, value, setting_type) VALUES
    ('meter_id', 'metadata.meter_sheet', '"meter_id_clean2"', 'str'),
    ('raw_uuid', 'metadata.meter_sheet', '"SEED_uuid"', 'str'),
    ('description', 'metadata.meter_sheet', '"description"', 'str'),
    ('building_level_meter', 'metadata.meter_sheet', '"Building Level Meter"', 'str'),
    ('meter_type', 'metadata.meter_sheet', '"Meter Type"', 'str'),
    ('reading_type', 'metadata.meter_sheet', '"class"', 'str'),
    ('units', 'metadata.meter_sheet', '"units_after_conversion"', 'str'),
    ('resolution', 'metadata.meter_sheet', '"Resolution"', 'str'),
    ('unit_conversion_factor', 'metadata.meter_sheet', '"unit_conversion_factor"', 'str'),
    ('tenant', 'metadata.meter_sheet', '"tenant"', 'str'),
    ('meter_building', 'metadata.meter_sheet', '"Building code"', 'str');

INSERT INTO settings (key, category, value, setting_type) VALUES
    ('building_code', 'metadata.building_sheet', '"Property code"', 'str'),
    ('building_name', 'metadata.building_sheet', '"Building Name"', 'str'),
    ('floor_area', 'metadata.building_sheet', '"floor_area"', 'str'),
    ('year_built', 'metadata.building_sheet', '"Year"', 'str'),
    ('usage', 'metadata.building_sheet', '"Function"', 'str'),
    ('maze_map_label', 'metadata.building_sheet', '"mazemap_ids"', 'str');

COMMIT;
```

### Commit [08eea80](https://github.com/ChristianAoC/energy-dashboard/commit/08eea8041118c731f2ab4e85d505887d4b04c5a3)
#### Created settings:
- server.meter_batch_size

```sql
BEGIN TRANSACTION;

INSERT INTO settings (key, category, value, setting_type) VALUES
    ('meter_batch_size', 'server', 16, 'int');

COMMIT;
```

### Commit [e0cc995](https://github.com/ChristianAoC/energy-dashboard/commit/e0cc9956cdc2f143cc84fed77334df30352e08c4)
#### Renamed settings:
- metadata.data_start_time => metadata.offline_data_start_time
- metadata.data_end_time => metadata.offline_data_end_time
- metadata.data_interval => metadata.offline_data_interval

```sql
BEGIN TRANSACTION;

UPDATE settings
SET key = 'offline_data_start_time'
WHERE key = 'data_start_time' AND category = 'metadata';

UPDATE settings
SET key = 'offline_data_end_time'
WHERE key = 'data_end_time' AND category = 'metadata';

UPDATE settings
SET key = 'offline_data_interval'
WHERE key = 'data_interval' AND category = 'metadata';

COMMIT;
```

#### Created settings:
- influx.data_interval

```sql
BEGIN TRANSACTION;

INSERT INTO settings (key, category, value, setting_type) VALUES
    ('data_interval', 'influx', 10, 'int');

COMMIT;
```