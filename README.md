gtfs-rt-metrics
===============

This is `gtfs-rt-metrics`, a project to collect metrics on [GTFS-realtime](https://developers.google.com/transit/gtfs-realtime/) feeds and log them to an [InfluxDB](https://docs.influxdata.com/influxdb/v1.5/) time-series database, where they can be visualized with [Grafana](https://grafana.com/), [Chronograph](https://docs.influxdata.com/chronograf/v1.5/), or other tools.

Deployment
----------

`gtfs-rt-metrics` is most easily deployed with [Docker](https://docs.docker.com/install/) and [Docker Compose](https://docs.docker.com/compose/):

1. Copy `config-sample.ini` to `config.ini` and edit as desired.  You may want to edit the list of feeds being monitored, change the polling interval, or alter the InfluxDB configuration parameters.
2. Copy `docker-compose-sample.yml` to `docker-compose.yml`.  Edit as desired (although no changes are required for the default configuration).
3. Build the `gtfs-rt-metrics` image with `docker-compose build`.
4. Start `gtfs-rt-metrics`, InfluxDB, and Grafana with `docker-compose up -d`.
5. If required, create the `rtmetrics` InfluxDB database (launch the `influx` client and run `CREATE DATABASE rtmetrics`).

Next Steps
----------

`gtfs-rt-metrics` will begin collecting the following metrics for each feed into InfluxDB every 20 seconds:

 * count of feed entities
 * count of trip updates, vehicle positions, and alerts
 * count of trip updates per route
 * age of feed header timestamp
 * average age of feed entity timestamp (only applicable to trip updates and vehicle positions)
 * feed response time
 * feed response size

All of the above are stored in an InfluxDB series called `feed_fetch`, except for the count of trip updates per route, which are stored in the `route_fetch` series.