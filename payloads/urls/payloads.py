#!/usr/bin/python3
import sqlite3
import argparse
import os

class Payloads:
    def create_new_index(self, database):
        con = sqlite3.connect(database)
        cur = con.cursor()
        sql = """ CREATE TABLE payloads (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     ts DATETIME,
                                     source_ip INTEGER,
                                     source_port INTEGER,
                                     url TEXT,
                                     sha1 TEXT,
                                     uid TEXT);
         """
        cur.execute(sql)

    def update_index(self, database, repository):
        for uuid in os.listdir(repository):
            print (uuid)

obj = Payloads()

parser = argparse.ArgumentParser(description="Sighting tests for files")
parser.add_argument("--create", action="store_true")
parser.add_argument("--repository", type=str, nargs=1, required=False)
parser.add_argument("--database", type=str, nargs=1, required=True)
args = parser.parse_args()

if args.create:
    obj.create_new_index(args.database[0])

obj.update_index(args.database[0], args.repository[0])
