#!/usr/bin/python3
import sqlite3
import argparse
import os
import hashlib
import sys
import time
import syslog

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
                                     length INTEGER,
                                     isref BOOL DEFAULT FALSE);
         """
        self.cur.execute(sql)
        sql = """ CREATE TABLE stage2 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                       ts DATETIME,
                                       uuid TEXT,
                                       filename TEXT,
                                       sha1 TEXT,
                                       length INTEGER,
                                       isref BOOL DEFAULT FALSE);
             """
        self.cur.execute(sql)

        sql = """ CREATE TABLE stage2_urls (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            url TEXT,
                                            uid TEXT);
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

    def update_stage2_urls(self, uid):
        fn = self.repository + os.sep + uid + os.sep + "stage2.urls"
        if os.path.exists(fn):
            with open(fn, "r") as f:
                for url in f.readlines():
                    url = url[:-1]
                    self.cur.execute("INSERT INTO stage2_urls (uid,url)\
VALUES (?,?);",[uid,url])

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
            try:
                d = self.repository + os.sep + uuid
                ts = self.get_timestamp(d)
                url = self.fetch_url(uuid)
                #TODO Record file size aswell
                stage1 = self.repository + os.sep + uuid + os.sep + "stage1.dat"
                h = self.compute_hash(stage1)
                l = int(os.stat(stage1).st_size)
                self.cur.execute("INSERT INTO payloads (ts, url, sha1,\
                    uid, length) VALUES (?,?,?,?,?)",[ts,url,h,uuid,l])
                self.update_stage2_urls(uuid)
                self.update_stage2(uuid)
            except sqlite3.IntegrityError as e:
                #Skip duplicates
                pass
            except FileNotFoundError as e:
                pass
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
        for (ts, sha1,uid) in self.cur.execute(
"SELECT strftime( datetime(ts,'unixepoch')) as date, sha1,uid FROM payloads \
WHERE  length > 0 GROUP BY SHA1 ORDER BY uid"):
            fn = self.repository + os.sep +  uid +  os.sep + "stage1.dat"
            print (ts, sha1,fn)

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

    def remove_stage2_files(self,  sha1):
        #First one is set as reference and should not be removed
        cnt = 0
        data= []
        for (id,uid,filename) in self.cur.execute("SELECT id, uuid,filename FROM stage2 \
                                            WHERE sha1 = ? ", [sha1]):
            data.append((id,uid,filename))

        for (id,uid,filename) in data:
            cnt+=1
            if cnt == 1:
                self.cur.execute("UPDATE stage2 SET isref=? WHERE id = ?;",
                                 [ "TRUE", id]);
                self.con.commit()
            else:
                fn = self.repository + os.sep + uid + os.sep + "stage2" + os.sep + filename
                if os.path.exists(fn):
                    syslog.syslog ("Removing:" + fn)
                    #TODO check if files were not marked to be kept by a
                    #previous run
                    os.unlink(fn)

    def remove_stage1_files(self,  sha1):
        #First one is set as reference and should not be removed
        cnt = 0
        data= []
        for (id,uid) in self.cur.execute("SELECT id, uid FROM payloads\
                                            WHERE sha1 = ? ", [sha1]):
            data.append((id,uid))

        for (id,uid) in data:
            cnt+=1
            if cnt == 1:
                self.cur.execute("UPDATE payloads SET isref=? WHERE id = ?;",
                                 [ "TRUE", id]);
                self.con.commit()
            else:
                fn = self.repository + os.sep + uid + os.sep + "stage1.dat"
                if os.path.exists(fn):
                    syslog.syslog ("Removing:" +fn)
                    #TODO check if files were not marked to be kept by a
                    #previous run
                    os.unlink(fn)
                    urlf = self.repository + os.sep + uid + os.sep + "stage1.url"
                    if os.path.exists(urlf):
                        syslog.syslog ("Removing: " + urlf)
                        os.unlink(urlf)

    def remove_duplicates_stage2(self):
        data = []
        for (ts,sha1) in self.cur.execute("SELECT ts,sha1 FROM stage2 WHERE\
                                      length > 0 GROUP BY SHA1\
                                      HAVING COUNT(*) > 1 ORDER BY ts;"):
            data.append(sha1)
        for  sha1 in data:
            self.remove_stage2_files(sha1)

    def remove_duplicates_stage1(self):
        data = []
        for (ts,sha1) in self.cur.execute("SELECT ts,sha1 FROM payloads WHERE\
                                      length > 0 GROUP BY SHA1\
                                      HAVING COUNT(*) > 1 ORDER BY ts;"):
            data.append(sha1)
        for  sha1 in data:
            self.remove_stage1_files(sha1)

    def clean_empty_directories(self):
        for uuid in os.listdir(self.repository):
            d = self.repository + os.sep + uuid + os.sep + "stage2"
            if os.path.exists(d):
                nfiles = len(os.listdir(d))
                if nfiles == 0:
                    syslog.syslog ("Removing " + d)
                    os.rmdir(d)
                    fn = self.repository + os.sep + uuid + os.sep + "stage2.urls"
                    if os.path.exists(fn):
                        syslog.syslog("Removing " + fn)
                        os.unlink(fn)

    def remove_empty_stage1(self):
        for uid in os.listdir(self.repository):
            fn =  self.repository + os.sep + uid + os.sep + "stage1.dat"
            if os.path.exists(fn):
                sz = os.stat(fn).st_size
                if sz == 0:
                    syslog.syslog("Removing " + fn)
                    os.unlink(fn)
                    urlf = self.repository + os.sep +  uid  + os.sep + "stage1.url"
                    if os.path.exists(urlf):
                        syslog.syslog("Removing " + urlf)
                        os.unlink(urlf)

    def remove_empty_uids(self):
        for uid in os.listdir(self.repository):
            d = self.repository + os.sep + uid
            if len(os.listdir(d)) == 0:
                syslog.syslog ("Removing "+ d)
                os.rmdir(d)

    def purge(self):
        self.remove_duplicates_stage2()
        self.remove_duplicates_stage1()
        self.clean_empty_directories()
        self.remove_empty_stage1()
        self.remove_empty_uids()

    def downloads_per_day(self):
        print("#Stage 1 downloads")
        print("#Day frequency")
        for date,cnt in self.cur.execute("SELECT \
                    STRFTIME(\"%Y-%m-%d\", DATETIME(ts,'unixepoch')) AS \
                    date, COUNT(*) FROM payloads GROUP BY date;"):
            print (date,cnt)
        print ("#Stage2 downloads")
        print("#Day frequency")
        for date,cnt in self.cur.execute("SELECT \
                    STRFTIME(\"%Y-%m-%d\", DATETIME(ts,'unixepoch')) AS \
                    date, COUNT(*) FROM stage2 GROUP BY date;"):
            print (date,cnt)

    def show_last_entries(self):
        for item in self.cur.execute("SELECT MAX(ts) FROM payloads;"):
            print ("stage1", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item[0])))
        for item in self.cur.execute("SELECT MAX(ts) FROM stage2;"):
            print ("stage2", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item[0])))


parser = argparse.ArgumentParser(description="Sighting tests for files")
parser.add_argument("--create", action="store_true")
parser.add_argument("--repository", type=str, nargs=1, required=True)
parser.add_argument("--database", type=str, nargs=1, required=True)
parser.add_argument("--hashes", action="store_true")
parser.add_argument("--duplicates", action="store_true")
parser.add_argument("--uid", type=str, nargs=1, required=False)
parser.add_argument("--purge", action="store_true")
parser.add_argument("--show", type=str)

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

if args.purge:
    obj.purge()
    sys.exit(0)

if args.show:
    if args.show == "help":
        print ("show download\t\tShow downlad histogram data extracted from the\
 database")
        print ("show last download\tShow the last download")
        sys.exit(1)

    if args.show == "download":
        obj.downloads_per_day()
    if args.show == "last download":
        obj.show_last_entries()
    sys.exit(0)
obj.update_index()
