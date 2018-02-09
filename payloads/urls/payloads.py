#!/usr/bin/python3
import sqlite3
import argparse
import os
import hashlib

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
                                     uid TEXT,
                                     length INTEGER);
         """
        self.cur.execute(sql)

    def get_timestamp(self, directory):
        #FIXME Get the download timestamp from filesystem
        #get it from somewhere else as it is error prone
        return int(os.stat(directory).st_ctime)

    def compute_hash(self, filename):
        m = hashlib.sha1()
        with open(filename,"rb") as f:
            m.update(f.read())
        return m.hexdigest()

    #TODO modify download script to add source ip, timestamp, source ip
    #in metadata file

    def update_index(self):
        for uuid in os.listdir(self.repository):
            d = self.repository + os.sep + uuid
            ts = self.get_timestamp(d)
            url = self.fetch_url(uuid)
            #TODO Record file size aswell
            stage1 = self.repository + os.sep + uuid + os.sep + "stage1.dat"
            h = self.compute_hash(stage1)
            l = int(os.stat(stage1).st_size)
            self.cur.execute("INSERT INTO payloads (ts, url, sha1,\
                uid, length) VALUES (?,?,?,?,?)",[ts,url,h,uuid,l])
        self.con.commit()

    def fetch_url(self,uuid):
        fn = self.repository + os.sep + uuid + os.sep + "stage1.url"
        url = None
        with open(fn, "r") as f:
            url = f.readline()
            url = url[:-1]
        return url

parser = argparse.ArgumentParser(description="Sighting tests for files")
parser.add_argument("--create", action="store_true")
parser.add_argument("--repository", type=str, nargs=1, required=True)
parser.add_argument("--database", type=str, nargs=1, required=True)
args = parser.parse_args()

obj = Payloads(args.database[0], args.repository[0])

if args.create:
    obj.create_new_index()

obj.update_index()
