from contextlib import contextmanager
from collections import namedtuple
import os
import glob
import csv
import psycopg2
from postgis.psycopg import register

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

Base = automap_base()
engine = create_engine("postgresql://hans:password@localhost:5432/gtfs")
Base.prepare(engine, reflect=True)

db = psycopg2.connect(host="localhost", dbname="gtfs", user="hans", password="password")
register(db)


@contextmanager
def load_csv(fname):
    """Utility function to handle csv loading"""
    name = os.path.basename(fname).replace(".txt", "")
    with open(fname) as f:
        reader = csv.reader(f)
        headers = next(reader)
        NamedTuple = namedtuple(name, headers)
        yield (NamedTuple, reader)


def import_to_db(names, reader, types={}):
    name = names.__name__
    fields = names._fields
    """
    columns = ", \n\t".join(
        '"{}" {}'.format(name, types.get(name, "VARCHAR")) for name in fields
    )
    sql = "CREATE TABLE IF NOT EXISTS {} (\n\t{}\n)".format(name, columns)
    """
    with db.cursor() as c:
        sql = """copy {} from '/gtfs/{}.txt' delimiter ',' csv header""".format(
            name, name
        )
        print(sql)
        c.execute(sql)
    db.commit()


def initial_load():
    with open("schema.sql") as f:
        with db.cursor() as c:
            schema = f.read()
            stmts = schema.split(";")
            for stmt in stmts:
                print("----")
                print(stmt.strip())
                if stmt.strip():
                    c.execute(stmt)
    for data in [
        "agency",
        "stops",
        "routes",
        "shapes",
        "trips",
        "stop_times",
        "calendar_dates",
        "transfers",
        "feed_info",
    ]:
        with load_csv("gtfs/{}.txt".format(data)) as (names, reader):
            import_to_db(names, reader)


# initial_load()
Base.prepare(engine, reflect=True)
# so find a stop based on a name
