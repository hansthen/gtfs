CREATE TABLE IF NOT EXISTS agency ( "agency_id" VARCHAR primary key,
	"agency_name" VARCHAR,
	"agency_url" VARCHAR,
	"agency_timezone" VARCHAR,
	"agency_phone" VARCHAR
);
CREATE TABLE IF NOT EXISTS stops (
	"stop_id" VARCHAR primary key,
	"stop_code" VARCHAR,
	"stop_name" VARCHAR,
	"stop_lat" FLOAT,
	"stop_lon" FLOAT,
	"location_type" INTEGER,
	"parent_station" VARCHAR,
	"stop_timezone" VARCHAR,
	"wheelchair_boarding" INTEGER,
	"platform_code" VARCHAR,
	"zone_id" VARCHAR
);
CREATE TABLE IF NOT EXISTS routes (
	"route_id" VARCHAR primary key,
	"agency_id" VARCHAR references agency,
	"route_short_name" VARCHAR,
	"route_long_name" VARCHAR,
	"route_desc" VARCHAR,
	"route_type" INTEGER,
	"route_color" VARCHAR,
	"route_text_color" VARCHAR,
	"route_url" VARCHAR
);
CREATE TABLE IF NOT EXISTS shapes (
	"shape_id" VARCHAR,
	"shape_pt_sequence"INTEGER,
	"shape_pt_lat" FLOAT,
	"shape_pt_lon" FLOAT,
	"shape_dist_traveled" FLOAT,
    primary key (shape_id, shape_pt_sequence)
);
CREATE TABLE IF NOT EXISTS trips (
	"route_id" VARCHAR references routes,
	"service_id" VARCHAR,
	"trip_id" VARCHAR primary key,
	"realtime_trip_id" VARCHAR,
	"trip_headsign" VARCHAR,
	"trip_short_name" VARCHAR,
	"trip_long_name" VARCHAR,
	"direction_id" INTEGER,
	"block_id" VARCHAR,
	"shape_id" VARCHAR,
	"wheelchair_accessible" INTEGER,
	"bikes_allowed" INTEGER
);
CREATE TABLE IF NOT EXISTS stop_times (
	"trip_id" VARCHAR references trips,
	"stop_sequence" INTEGER,
	"stop_id" VARCHAR references stops,
	"stop_headsign" VARCHAR,
	"arrival_time" VARCHAR,
	"departure_time" VARCHAR,
	"pickup_type" INTEGER,
	"drop_off_type" INTEGER,
	"timepoint" INTEGER,
	"shape_dist_traveled" FLOAT,
	"fare_units_traveled" VARCHAR,
    primary key (trip_id, stop_sequence)
);
CREATE TABLE IF NOT EXISTS calendar_dates (
	"service_id" VARCHAR,
	"date" VARCHAR,
	"exception_type" INTEGER,
    primary key (service_id, date)
);
CREATE TABLE IF NOT EXISTS transfers (
	"from_stop_id" VARCHAR references stops,
	"to_stop_id" VARCHAR references stops,
	"from_route_id" VARCHAR references routes,
	"to_route_id" VARCHAR references routes,
	"from_trip_id" VARCHAR references trips,
	"to_trip_id" VARCHAR references trips,
	"transfer_type" INTEGER,
    primary key (from_stop_id, to_stop_id, from_route_id, to_route_id, from_trip_id, to_trip_id)
);
CREATE TABLE IF NOT EXISTS feed_info (
	"feed_publisher_name" VARCHAR,
	"feed_id" VARCHAR primary key,
	"feed_publisher_url" VARCHAR,
	"feed_lang" VARCHAR,
	"feed_start_date" VARCHAR,
	"feed_end_date" VARCHAR,
	"feed_version" VARCHAR
);

-- load data from csv
copy agency from '/gtfs/agency.txt' delimiter ',' csv header;
copy stops from '/gtfs/stops.txt' delimiter ',' csv header;
copy routes from '/gtfs/routes.txt' delimiter ',' csv header;
copy shapes from '/gtfs/shapes.txt' delimiter ',' csv header;
copy trips from '/gtfs/trips.txt' delimiter ',' csv header;
copy stop_times from '/gtfs/stop_times.txt' delimiter ',' csv header;
copy calendar_dates from '/gtfs/calendar_dates.txt' delimiter ',' csv header;
copy transfers from '/gtfs/transfers.txt' delimiter ',' csv header;
copy feed_info from '/gtfs/feed_info.txt' delimiter ',' csv header;

-- a few useful indices
create index on stop_times(arrival_time);
create index on stop_times(stop_id);
create index on stop_times(trip_id);
create index on calendar_dates(date);
create index on trips(service_id);
create index on stops(stop_code);

-- a few useful views
create view later_stop_times as select * from stop_times where arrival_time > to_char(current_timestamp, 'HH24:MI:SS') order by arrival_time;
create view active_services as select * from calendar_dates where date = to_char(current_date, 'YYYYMMDD');
create view active_trips as select * from trips where service_id in (select service_id from active_services);
