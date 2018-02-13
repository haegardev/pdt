#!/usr/bin/python3
import sqlite3
import argparse
import os
import hashlib
import sys

class Payloads:

    def __init__(self, database, repository):
        self.database = database
        self.repository = repository
        self.con = sqlite3.connect(database)
        self.con.isolation_level=None
        self.cur = self.con.cursor()

    def create_new_index(self):
        sql = """ CREATE TABLE payloads (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     ts DATETIME,
                                     source_ip INTEGER,
                                     source_port INTEGER,
                                     url TEXT,
                                     sha1 TEXT,
                                     uid TEXT UNIQUE,
                                     length INTEGER);
         """
        self.cur.execute(sql)
        sql = """ CREATE TABLE stage2 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                       ts DATETIME,
                                       uuid TEXT,
                                       filename TEXT,
                                       sha1 TEXT,
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

    def update_stage2(self, uuid):
        d = self.repository + os.sep + uuid +  os.sep  +"stage2"
        if os.path.exists(d):
            for i in os.listdir(d):
                fn = d + os.sep + i
                ts = self.get_timestamp(fn)
                hsh = self.compute_hash(fn)
                sz  = int(os.stat(fn).st_size)
                self.cur.execute("INSERT INTO stage2 \
                                  (ts, uuid, filename, sha1, length)\
                                  VALUES (?,?,?,?,?);",[ts, uuid, i, hsh, sz])
#TODO modify download script to add source ip, timestamp, source ip
    #in metadata file

    def update_index(self):
        self.con.execute('BEGIN TRANSACTION')
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
            self.update_stage2(uuid)
        #self.con.commit()
        self.con.execute('END TRANSACTION')

    def fetch_url(self,uuid):
        fn = self.repository + os.sep + uuid + os.sep + "stage1.url"
        url = None
        with open(fn, "r") as f:
            url = f.readline()
            url = url[:-1]
        return url

    def print_hashes(self):
        for (sha1,uid) in self.cur.execute("SELECT sha1,uid FROM payloads WHERE  length > 0 GROUP BY SHA1 ORDER BY uid"):
            fn = self.repository + os.sep +  uid +  os.sep + "stage1.dat"
            print (sha1,fn)

    #FIXME stage1.dat can be the same but stage2 different
    def duplicate_info(self):
        print ("#uid,sha1,count")
        for (uid,sha1,count) in self.cur.execute("SELECT uid,sha1,COUNT(*) \
                                FROM payloads WHERE length > 0 GROUP BY sha1 \
                                HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC;"):
            print (uid,sha1,count)

    def query_uid(self, sha1):
        for (uid,sha1) in self.cur.execute("SELECT uid,sha1 FROM payloads WHERE sha1 = ? ",[sha1]):
            print (self.repository + os.sep + uid + os.sep + "stage1.dat")

parser = argparse.ArgumentParser(description="Sighting tests for files")
parser.add_argument("--create", action="store_true")
parser.add_argument("--repository", type=str, nargs=1, required=True)
parser.add_argument("--database", type=str, nargs=1, required=True)
parser.add_argument("--hashes", action="store_true")
parser.add_argument("--duplicates", action="store_true")
parser.add_argument("--uid", type=str, nargs=1, required=False)

args = parser.parse_args()

obj = Payloads(args.database[0], args.repository[0])

if args.create:
    obj.create_new_index()
if args.hashes:
    obj.print_hashes()
    sys.exit(0)

if args.duplicates:
    obj.duplicate_info()
    sys.exit(0)

if args.uid:
    obj.query_uid(args.uid[0])
    sys.exit(0)
obj.update_index()
