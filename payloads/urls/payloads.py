#!/usr/bin/python3
import sqlite3
import argparse
import os

class Payloads:
    def __init__(self, database, repository):
        self.database = database
        self.repository = repository
        self.con = sqlite3.connect(database)
        self.cur = self.con.cursor()

    def create_new_index(self):
        sql = """ CREATE TABLE payloads (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     ts DATETIME,
                                     source_ip INTEGER,
                                     source_port INTEGER,
                                     url TEXT,
                                     sha1 TEXT,
                                     uid TEXT);
         """
        self.cur.execute(sql)

    def get_timestamp(self, directory):
        #FIXME Get the download timestamp from filesystem
        #get it from somewhere else as it is error prone
        return int(os.stat(d).st_ctime)

    #TODO modify download script to add source ip, timestamp, source ip
    #in metadata file

    def update_index(self):
        for uuid in os.listdir(self.repository):
            d = self.repository + os.sep + uuid
            ts = self.get_timestamp(d)


parser = argparse.ArgumentParser(description="Sighting tests for files")
parser.add_argument("--create", action="store_true")
parser.add_argument("--repository", type=str, nargs=1, required=True)
parser.add_argument("--database", type=str, nargs=1, required=True)
args = parser.parse_args()

obj = Payloads(args.database[0], args.repository[0])

if args.create:
    obj.create_new_index()

obj.update_index()
