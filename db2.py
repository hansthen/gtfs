from contextlib import contextmanager
from collections import namedtuple
import os
import glob
import csv
import psycopg2
from postgis.psycopg import register

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base

app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://hans:password@localhost:5432/gtfs"
db = SQLAlchemy(app)
db.Model = automap_base(db.Model)
db.Model.prepare(db.engine, reflect=True)

print(db.Session)
Stop = db.Model.classes.stops
print(Stop)

print(Stop.query.first())
