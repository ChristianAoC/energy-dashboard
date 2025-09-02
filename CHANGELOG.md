# Changelog
## Pre-Release
This list contains the breaking changes for individual commits (anything that needs to be manually changed on the server).

### Commit [e0cc995](https://github.com/ChristianAoC/energy-dashboard/commit/e0cc9956cdc2f143cc84fed77334df30352e08c4)
#### Renamed settings:
- metadata.data_start_time => metadata.offline_data_start_time
- metadata.data_end_time => metadata.offline_data_end_time
- metadata.data_interval => metadata.offline_data_interval

#### Created settings:
- influx.data_interval
