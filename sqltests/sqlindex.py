#!/usr/bin/python3
import socket, struct
import sqlite3
import argparse
import sys
import pprint
import os
import redis
import time
import syslog

#TODO add debug messages including PIDs.
#FIXME Jobs are removed although they are not fully consumed?
class SQLIndex:

    def __init__(self, database, dbg=True):
        if database is not None:
            self.con = sqlite3.connect(database)
            self.con.isolation_level=None
            self.cur = self.con.cursor()
            self.database = database
            self.dbg = dbg
        else:
            self.con = None
        #FIXME Set parameter if multiple servers are used for serving indices
        self.instance="127.0.0.1"
        self.redis_server="127.0.0.1"
        self.redis_port=6379
        if self.dbg == True:
            syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_USER)

    def __del__(self):
        if self.con is not None:
            self.con.close()

    def log(self, msg):
        syslog.syslog(msg)

    def create_schema(self):
        sql = """CREATE TABLE flows (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    source_id INTEGER,
                                    frameno INTEGER,
                                    ts DATETIME,
                                    source_ip INTEGER,
                                    source_port INTEGER,
                                    destination_ip INTEGER,
                                    destination_port INTEGER,
                                    protocol INTEGER,
                                    ttl INTEGER,
                                    tcpseq INTEGER,
                                    tcpflags INTEGER,
                                    tcpack INTEGER);
          """
        self.cur.execute(sql)
        sql = """CREATE TABLE sources (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   name TEXT);
          """
        self.cur.execute(sql)
        self.log("Create database scheme in " + self.database)
    #Read from data from stdin and put them in the database

    def update_index(self, filename):
        #TODO check if file was already indexed
        #Get unique source id
        #FIXME not atomic assume one writer per database
        x = self.cur.execute("INSERT INTO sources  (name) values  (?);", [filename] )
        #FIXME does not work
        #print (cur.last_insert_rowid());
        self.cur.execute("SELECT max(id) FROM sources;")
        source_id = self.cur.fetchone()[0]
        values = []
        self.con.execute('BEGIN TRANSACTION')
        cnt=0
        for line in sys.stdin.readlines():
            line = line[:-1]
            (frameno,ts, proto, source_ip,udp_source_port, tcp_source_port, destination_ip,
            udp_destination_port, tcp_destination_port, ttl,seq,tcpflags,tcpack)  = line.split("|")
            source_port = -1
            destination_port = -1
            iseq = None
            iack = None
            frameno = int(frameno)

            if udp_source_port == "":
                if tcp_source_port != "":
                    source_port = int(tcp_source_port)
            else:
                if udp_source_port != "":
                    source_port = int(udp_source_port)

            #
            if udp_destination_port == "":
                if tcp_destination_port != "":
                    destination_port = int(tcp_destination_port)
            else:
                if udp_destination_port != "":
                    destination_port = int(udp_destination_port)
            #print ("line "+line)
            #print ("ts  "+ ts)
            #print ("proto " +proto)
            #print ("Source_ip " + source_ip)
            #print ("Source_port " + str(source_port))
            #print ("destination_ip "+destination_ip)
            #print ("destination_port "+str(destination_port))
            #print ("ttl "+ str(ttl))
            #print ("tcpflags "+ tcpflags)
            if tcpflags != "":
                tcpflags = int(tcpflags,16)
            if source_ip == "" or destination_ip == "":
                continue
            x = socket.inet_aton(destination_ip)
            dip = struct.unpack("!L", x)[0]

            x = socket.inet_aton(source_ip)
            sip = struct.unpack("!L",x)[0]
            try:
                iseq = int(seq)
                iack = int(tcpack) #FIXME better error handling
            except ValueError as w:
                pass
            self.cur.execute("INSERT INTO flows (source_id, frameno, ts,source_ip, source_port,\
                destination_ip, destination_port, protocol,ttl,tcpseq,\
                tcpflags,tcpack) \
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [source_id,frameno, ts,sip,source_port, dip, destination_port,int(proto), int(ttl), iseq, tcpflags,iack ])
            cnt+=1
        self.log("Inserted "+ str(cnt) + " packets into "+self.database)
        self.con.execute('END TRANSACTION')

    #Modify dotted decimal IP addresses
    #TODO Translate subnet queries into logical and arithmetic operations
    #TODO Document query language
    #Buf can be a redis key where the data is submitted by a worker
    #TODO create ordered query. add timestamp and use a ZRANK as buffer
    def query(self,sqlstring,buf=None):
        red =  None
        if buf is not None:
            red = redis.Redis(host=self.redis_server,port=self.redis_port)
        q = sqlstring
        ips = []
        words = sqlstring.split(" ")
        for word in words:
            for nword in word.split("="):
                if nword.count(".") == 3:
                    nword = nword.replace("\"", "")
                    nword = nword.replace(";","")
                    ips.append(nword)
        for ip in ips:
            iip = socket.inet_aton(ip)
            iiip = struct.unpack("!L", iip)[0]
            q = q.replace("\""+ip+"\"",str(iiip))
        print ("Modified query " + q)
        #FIXME output is not clean
        #TODO Check output length to avoid to write several GB of data in the
        #output queue
        if red is None:
            for i in self.cur.execute(q):
                print (i)
        else:
            for i in self.cur.execute(q):
                #Execution order of the workers is not known and are in parallel
                #If the job_id is anymore in JOB set the query is done
                #TODO Link the query with the results
                red.sadd(buf,i)

    #Returns True if the job was completed
    #Returns False if the job is not completed
    def consume_buffer(self, job_id, blocking=True):
        red = redis.Redis(host=self.redis_server,port=self.redis_port)
        key = self.instance + "_RESULTS_" + job_id
        while True:
            for chunk in red.smembers(key):
                print (chunk)
                red.delete(key,chunk)
            key = self.instance +"_JOBS"
            if red.sismember(key, job_id):
                print ("The job is not done yet")
                if blocking:
                    print ("Wait a bit")
                    time.sleep(0.5)
                else:
                    return False
            else:
                print ("Job is done, exit")
                return True
        return True

    #TODO check filemagic of databases that are added
    def sync_database_files(self, directory):
        red = redis.Redis(host=self.redis_server,port=self.redis_port)
        key = self.instance + "_" + "DATABASES"
        for root, subdirs, files in os.walk(directory):
            for f in files:
                fn = root + os.sep + f
                red.sadd(key, fn)

    def submit_query(self,query):
        red = redis.Redis(host=self.redis_server, port=self.redis_port)
        #FIXME Not executed atomicly. The copying process of the databases
        #can be interfered with a worker removing the job id
        #Keep order of jobs. Get new JOB_ID
        job_id = red.incr(self.instance+"_JOB_ID")
        red.set("QUERY_JOB_"+str(job_id), query)
        #TODO create rules for restricting databases where to look at
        databases = []
        for db in red.smembers(self.instance + "_DATABASES"):
            databases.append(db)
        databases.sort()
        for db in databases:
            key = self.instance + "_JOB_" + str(job_id)
            red.rpush(key,db)
        red.sadd(self.instance + "_JOBS", job_id)
        return job_id

    #returns the oldest job_id. If no job is there it returns 0
    def get_oldest_job_id(self):
        red = redis.Redis(host=self.redis_server, port=self.redis_port)
        min_id = sys.maxsize
        for i in red.smembers(self.instance + "_JOBS"):
            i = int(i)
            if i<min_id:
                min_id = i
        if min_id == sys.maxsize:
            min_id = 0
        return min_id

    def execute_query(self, job_id, dbfile,query):
        f = dbfile.decode("ASCII")
        query = query.decode("ASCII")
        self.con = sqlite3.connect(f)
        self.cur = self.con.cursor()
        buf = self.instance + "_RESULTS_" + str(job_id)
        self.query(query, buf)
        self.con.close()
        #TODO add exception handling here

    def worker(self):
        red = redis.Redis(host=self.redis_server, port=self.redis_port)
        job_id = self.get_oldest_job_id()
        if job_id > 0:
            key = self.instance + "_JOB_" + str(job_id)
            dbfile = red.lpop(key)
            if dbfile:
                query = red.get("QUERY_JOB_"+str(job_id))
                if query:
                    self.execute_query(job_id, dbfile, query)
            else:
                #Queue is empty. Remove it from the jobs set
                red.srem(self.instance + "_JOBS", job_id)
                #TODO remove query when the data is consumed

    #FIXME Busy waiting. However, redis pub sub does not seem to buffer
    def worker_loop(self):
        while True:
            self.worker()
            time.sleep(0.5)

parser = argparse.ArgumentParser(description="test for importing pcaps in sqlite3")
parser.add_argument("--create", action='store_true')
parser.add_argument("--database", type=str, nargs=1, required=False)
parser.add_argument("--query", type=str, nargs=1, required=False,
                    help="Execute an SQL query on the database. IP addresses\
 in the query string are translated from dotted decimal into binary values.")
parser.add_argument("--filename",type=str,nargs=1,required=False,
                    help="Read input from stdin and insert it into flows table. \
The filename parameter helps to propagte the filename into the sources table. \
The indexing is started when this parameter is set.")
parser.add_argument("--sync",type=str,nargs=1, help="Update redis key\
 <HOST>_DATABASES with database files in the specified directory")

parser.add_argument("--submit", type=str, nargs=1, help="Submit an sql query\
to the indices")

parser.add_argument("--worker", action='store_true', help="Start worker who are\
waiting for queries of the indexes. Choose the oldest job by default.")

parser.add_argument("--consume", type=str, nargs=1, required=False,
                    help="Print the data produced on stdout")

args = parser.parse_args()
database=args.database
if database is not None:
    database = args.database[0]

sqi = SQLIndex(database)

if args.create:
    sqi.create_schema()

if args.filename:
    sqi.update_index(args.filename[0])

if args.query:
    sqi.query(args.query[0])
    sys.exit(0)

if args.sync:
    sqi.sync_database_files(args.sync[0])
    sys.exit(0)

if args.submit:
    print(sqi.submit_query(args.submit[0]))
    sys.exit(0)

if args.worker:
    sqi.worker_loop()

if args.consume:
    #FIXME ignore return code
    sqi.consume_buffer(args.consume[0])
    sys.exit(0)
