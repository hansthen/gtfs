import zmq
import time
from gzip import GzipFile
import io
import csv
import sys

import itertools
import matplotlib.pyplot as plt
import logging
import os
import smopy
import geocoder
from datetime import datetime, timedelta
from collections import defaultdict, namedtuple
import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
import geoalchemy2

import configargparse

logging.basicConfig(
    level=os.getenv("LOGLEVEL", "WARNING"),
    format=os.getenv("LOGFORMAT", "%(asctime)s;%(levelname)s;%(message)s"),
)

#########################################################
# Load and filter the gtfs feed data
#########################################################

Base = automap_base()
engine = create_engine("postgresql://hans:password@localhost:5432/gtfs")
Session = sessionmaker(bind=engine)
metadata = MetaData()
metadata.reflect(engine, views=True)
Base = automap_base(metadata=metadata)
Base.prepare()

Stop = Base.classes.stops
Service = Base.classes.calendar_dates
Trip = Base.classes.trips
Shape = Base.classes.shapes
Route = Base.classes.routes
Schedule = Base.classes.stop_times


class GtfsDisplay:
    def __init__(self, args):
        today = datetime.now().strftime("%Y%m%d")
        logging.warning(today)
        self.session = Session()
        self.location = args.show
        self.routes = args.route
        self.agencies = args.agency
        self.trips = (
            self.session.query(Trip)
            .filter(
                Trip.route_id.in_(
                    self.session.query(Route.route_id).filter(
                        Route.route_short_name.in_(args.route),
                        Route.agency_id.in_(args.agency),
                    )
                )
            )
            .filter(
                Trip.service_id.in_(
                    self.session.query(Service.service_id).filter(Service.date == today)
                )
            )
            .all()
        )
        for i, trip in enumerate(self.trips):
            trip.shape = (
                self.session.query(Shape)
                .filter(Shape.shape_id == trip.shape_id)
                .order_by(Shape.shape_pt_sequence)
                .all()
            )
            trip.first = trip.stop_times_collection[0]
            trip.last = trip.stop_times_collection[-1]

    ################################################################
    # Create and display the basic map
    ################################################################
    def show_map(self, name):
        """Display the map for a location"""
        g = geocoder.osm(name)
        bbox = g.json["bbox"]
        bbox = bbox["northeast"] + bbox["southwest"]
        map_ = smopy.Map(bbox, zoom=11)
        logging.debug("Bounding box: %s", map_.box)
        ax = map_.show_mpl(figsize=(10, 6))
        xs = []
        ys = []

        # This show all stops on the map, also not the ones
        # used for processing, but heck . . .
        lat_ne, lon_ne, lat_sw, lon_sw = bbox
        stops = (
            self.session.query(Stop)
            .filter(
                Stop.stop_lat <= lat_ne,
                Stop.stop_lat >= lat_sw,
                Stop.stop_lon <= lon_ne,
                Stop.stop_lon >= lon_sw,
            )
            .all()
        )

        for stop in stops:
            x, y = map_.to_pixels(stop.stop_lat, stop.stop_lon)
            xs.append(x)
            ys.append(y)

        plt.ion()
        plt.show()
        ax.plot(xs, ys, ".c")

        # Plot the tracks in blue
        for trip in self.trips:
            shape = trip.shape
            xys = [
                map_.to_pixels(element.shape_pt_lat, element.shape_pt_lon)
                for element in shape
            ]

            xs = [elem[0] for elem in xys]
            ys = [elem[1] for elem in xys]
            ax.plot(xs, ys, "-b")

        plt.pause(0.001)

        return map_, ax

    #################################################################
    # Process updates from the ov feed on openov.nl
    #################################################################

    def subscribe_ov_feed(self, map_, ax, locks, stop_flag):
        #
        return

        context = zmq.Context()
        kv8 = context.socket(zmq.SUB)
        kv8.connect("tcp://kv7.openov.nl:7817")
        kv8.setsockopt(zmq.SUBSCRIBE, b"/GOVI/KV8")

        poller = zmq.Poller()
        poller.register(kv8, zmq.POLLIN)

        while not stop_flag.wait(0.0):
            keys = []
            socks = dict(poller.poll())
            if socks.get(kv8) == zmq.POLLIN:
                multipart = kv8.recv_multipart()
                content = GzipFile(
                    "", "r", 0, io.BytesIO(b"".join(multipart[1:]))
                ).read()
                for line in content.split(b"\n"):
                    line = line.decode("utf-8")
                    if line.startswith("\L"):
                        keys = line[2:].split("|")
                        continue
                    # Hacky, reduce the nr of updates based on what I am interested in
                    # if not line.startswith("RET"):
                    #    continue
                    values = line.split("|")
                    d = {key: value for (key, value) in zip(keys, values)}
                    if (
                        "UserStopCode" in d
                        and d["UserStopCode"] in self.stops_by_stop_code
                    ):
                        stop = self.stops_by_stop_code[d["UserStopCode"]]
                        stop_id = stop[0]

                        # I ignored a few of the updates for now
                        # Most importantly, I do not check for cancelled stops
                        # A first version only checked for Metro lines, but that
                        # is commented now
                        # if not d["LinePlanningNumber"].startswith("M"):
                        #    continue
                        base = datetime.strptime(d["OperationDate"], "%Y-%m-%d")
                        expected_arrival = normalize(d["ExpectedArrivalTime"], base)
                        expected_departure = normalize(d["ExpectedDepartureTime"], base)

                        journey = d["JourneyNumber"]
                        if journey not in self.trips_by_journey:
                            continue
                        trip = self.trips_by_journey[d["JourneyNumber"]]
                        lock = locks[trip[2]]
                        with lock:
                            journey = self.schedule[trip[2]]
                            for index, item in enumerate(journey):
                                if item.stop_id == stop_id:
                                    break
                            else:
                                continue

                            if item.arrival_time != expected_arrival:
                                logging.debug(
                                    "%s %s %s",
                                    item,
                                    repr(expected_arrival),
                                    repr(expected_departure),
                                )
                                journey[index] = item._replace(
                                    arrival_time=expected_arrival,
                                    departure_time=expected_departure,
                                )

    #######################################################
    # Periodically draw the location of a trip on the map
    #######################################################
    def update_map(self, map_, ax, locks):
        """ Update the map with the current vehicle locations.
        """
        logging.debug("Start updating map")
        dots = []

        def pairwise(iterable):
            "s -> (s0,s1), (s1,s2), (s2, s3), ..."
            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        while True:
            logging.debug("Updating . . . ")
            try:
                for dot in dots:
                    dot[0].remove()
                dots = []

                # FIXME: this breaks after midnight. Need
                # to translate now back to the service date
                now = datetime.now().strftime("%H:%M:%S")
                xs = []
                ys = []

                for trip in self.trips:
                    if trip.first.arrival_time > now or trip.last.departure_time < now:
                        continue
                    id_ = trip.trip_id
                    lock = threading.Lock()
                    with lock:
                        stop_times = trip.stop_times_collection
                        for start, stop in pairwise(stop_times):
                            if stop.arrival_time <= now <= stop.departure_time:
                                # vehicle is currently at a stop
                                # Get the stops object associated with this stop_times object
                                stop_info = stop.stops
                                # stop_info = self.stops[stop.stop_id]
                                x, y = map_.to_pixels(
                                    float(stop_info.stop_lat), float(stop_info.stop_lon)
                                )
                                dots.append(ax.plot(x, y, "or"))
                                break
                            elif start.departure_time < now < stop.arrival_time:
                                # vehicle is driving, determine exact location

                                # find the ratio of current segment in time
                                ratio = point_ratio(
                                    normalize(now),
                                    normalize(start.departure_time),
                                    normalize(stop.arrival_time),
                                )

                                # now find the location in distance
                                # / assuming constant speed :-(
                                mid = int(
                                    weighted(
                                        ratio,
                                        start.shape_dist_traveled or 0.0,
                                        stop.shape_dist_traveled or 0.0,
                                    )
                                )

                                # shape = self.shapes[self.trips[id_][9]]
                                if not trip.shape_id:
                                    continue

                                shape = trip.shape

                                if not shape:
                                    logging.warning(
                                        "Shape for trip %s, %s is empty",
                                        id_,
                                        trip.shape_id,
                                    )
                                    break
                                else:
                                    logging.debug(
                                        "Shape for trip %s, %s is fine",
                                        id_,
                                        trip.shape_id,
                                    )

                                # find the corresponding line segment
                                seg_start, seg_end = find_surrounding(
                                    shape,
                                    mid,
                                    key=lambda x, mid: mid.shape_dist_traveled <= x,
                                )

                                # determine the ratio of the line segment
                                ratio = point_ratio(
                                    mid,
                                    seg_start.shape_dist_traveled,
                                    seg_end.shape_dist_traveled,
                                )

                                # translate to lat, lon
                                vehicle_lat = weighted(
                                    ratio, seg_start.shape_pt_lat, seg_end.shape_pt_lat
                                )
                                vehicle_lon = weighted(
                                    ratio, seg_start.shape_pt_lon, seg_end.shape_pt_lon
                                )

                                # translate from coords to pixels
                                x, y = map_.to_pixels(vehicle_lat, vehicle_lon)

                                # save for drawing on map later
                                xs.append(x)
                                ys.append(y)
                                break
                            else:
                                # this stop_time does not match anything
                                pass
                        else:
                            # we went through the stop_times loop, but without breaks
                            # this should not happen
                            logging.warning(
                                "This trip is inactive, it should have been skipped"
                            )

                # draw the saved locations on map
                logging.warning("draw")
                dots.append(ax.plot(xs, ys, "om"))
                plt.pause(0.001)
                time.sleep(0.001)
            except KeyboardInterrupt:
                break

    def start(self):
        map_, ax = self.show_map(self.location)
        locks = {}
        stop = threading.Event()
        thread = threading.Thread(
            target=self.subscribe_ov_feed, args=[map_, ax, locks, stop]
        )
        thread.start()
        self.update_map(map_, ax, locks)
        stop.set()
        thread.join()


def point_ratio(point, start, end):
    """Find the ratio of two points on a line divided by a third"""
    return (end - point) / (end - start)


def weighted(ratio, start, end):
    """Given a ratio, find the weighted average of two points"""
    return ratio * start + (1 - ratio) * end


def find_surrounding(a, x, key=lambda x, mid: mid <= x):
    """Find the two elements in an array surrounding a point"""
    assert len(a) > 0, "no data in array"

    hi, lo = len(a), 0
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid].shape_dist_traveled <= x:
            lo = mid + 1
        else:
            hi = mid
    return a[lo - 1], a[lo]


def normalize(
    time_string, base=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
):
    """Normalize a time specified in 24h+ notation into a python date"""
    hours, minutes, seconds = time_string.split(":")
    delta = timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))
    return base + delta


def get_parser():
    parser = configargparse.ArgParser()
    parser.add("--show", default="Rotterdam")
    parser.add("-r", "--route", action="append")
    parser.add("-a", "--agency", action="append")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    display = GtfsDisplay(args)
    display.start()


if __name__ == "__main__":
    main()
