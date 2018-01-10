import argparse
import configparser
import logging
from datetime import datetime
from statistics import mean

import requests
from requests.exceptions import RequestException
from google.transit import gtfs_realtime_pb2
from google.protobuf.message import Error as ProtobufError
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR
from influxdb import InfluxDBClient

def get(agency_id, feed_id, feed_url, influxdb_config, timeout):
    now = datetime.utcnow()

    point = {
        "measurement": "feed_fetch",
        "tags": {
            "agency_id": agency_id,
            "feed_id": feed_id,
            "feed_url": feed_url
            },
        "time": now,
        "fields": {
            }
    }

    try:
        response = requests.get(feed_url, timeout=timeout)

        if response.status_code is not None:
            point['fields']['status_code'] = str(response.status_code)

        if response.elapsed is not None:
            point['fields']['response_time_ms'] = response.elapsed.total_seconds() * 1000

        if response.content is not None:
            point['fields']['response_size_bytes'] = len(response.content)

        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        point['fields']['entity_count'] = 0
        point['fields']['trip_update_count'] = 0
        point['fields']['vehicle_position_count'] = 0
        point['fields']['alert_count'] = 0

        if feed.header.HasField('timestamp'):
            point['fields']['header_ts_age_ms'] = (now - datetime.utcfromtimestamp(feed.header.timestamp)).total_seconds() * 1000

        entity_timestamps = []

        for entity in feed.entity:
            point['fields']['entity_count'] += 1

            if entity.HasField('trip_update'):
                point['fields']['trip_update_count'] += 1

            if entity.HasField('vehicle'):
                point['fields']['vehicle_position_count'] += 1

            if entity.HasField('alert'):
                point['fields']['alert_count'] += 1

            if entity.HasField('trip_update') and entity.trip_update.HasField('timestamp'):
                entity_timestamps.append(entity.trip_update.timestamp)

            if entity.HasField('vehicle') and entity.vehicle.HasField('timestamp'):
                entity_timestamps.append(entity.vehicle.timestamp)

        entity_timestamp_ages_ms = [(now - datetime.utcfromtimestamp(ts)).total_seconds() * 1000
                                    for ts
                                    in entity_timestamps]

        if len(entity_timestamp_ages_ms) > 0:
            point['fields']['entity_timestamp_ages_min_ms'] = min(entity_timestamp_ages_ms)
            point['fields']['entity_timestamp_ages_max_ms'] = max(entity_timestamp_ages_ms)
            point['fields']['entity_timestamp_ages_avg_ms'] = mean(entity_timestamp_ages_ms)

    except (RequestException, ProtobufError) as e:
        logging.warning("Exception caught while fetching feed %s from %s:", feed_id, feed_url, exc_info=True)
        point['fields']['error'] = str(e)

    client = InfluxDBClient(**influxdb_config)
    
    client.write_points([point], time_precision="s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect metrics from GTFS-rt feeds and log to InfluxDB")
    parser.add_argument('config_file', type=argparse.FileType('r'), help="Configuration file")
    parser.add_argument('--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='WARNING',
                        help="Log level")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log))

    config = configparser.ConfigParser()
    config.read_file(args.config_file)

    scheduler = BlockingScheduler()

    scheduler.add_listener(lambda event: logging.error("Exception in feed fetch:",
                                                       exc_info=event.exception),
                           EVENT_JOB_ERROR)

    interval = int(config['interval']['interval'], 10)
    agency_ids = [key.split(':')[1] for key in config.keys() if key.startswith('agency:')]

    for agency_id in agency_ids:
        for feed in config['agency:' + agency_id].items():
            (feed_id, feed_url) = feed
            scheduler.add_job(get,
                              'interval',
                              (agency_id, feed_id, feed_url, config['influxdb'], interval / 2),
                              seconds=interval,
                              id=agency_id + ":" + feed_id)

    scheduler.start()
