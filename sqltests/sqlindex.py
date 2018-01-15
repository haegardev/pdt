#!/usr/bin/python3
import socket, struct
import sqlite3
import argparse
import sys
import pprint
parser = argparse.ArgumentParser(description="test for importing pcaps in sqlite3")
parser.add_argument("--create", action='store_true')
parser.add_argument("--database", type=str, nargs=1, required=True)
parser.add_argument("--query", type=str, nargs=1, required=False)
parser.add_argument("--filename",type=str,nargs=1,required=False)
args = parser.parse_args()

filename = None
if args.filename:
    filename = args.filename[0]

source_id = 0 # Source index 0 is undefined
con = sqlite3.connect(args.database[0])
con.isolation_level=None
cur = con.cursor()
if args.query:
    q = args.query[0]
    print (args.query[0])
    #Search for dotted decimal notatioons and convert them
    #FIXME Improve this
    ips = []
    words = args.query[0].split(" ")
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
        for i in cur.execute(q):
            print (i)
    sys.exit(1)

if args.create:
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
    cur.execute(sql)
    sql = """CREATE TABLE sources (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   name TEXT);
          """
    cur.execute(sql)

#Get unique source id
x = cur.execute("INSERT INTO sources  (name) values  (?);", [filename] )
#FIXME does not work
#print (cur.last_insert_rowid());
cur.execute("SELECT max(id) FROM sources;")
source_id = cur.fetchone()[0]
values = []
con.execute('BEGIN TRANSACTION')
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
    cur.execute("INSERT INTO flows (source_id, frameno, ts,source_ip, source_port,\
                destination_ip, destination_port, protocol,ttl,tcpseq,\
                tcpflags,tcpack) \
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [source_id,frameno, ts,sip,source_port, dip, destination_port,int(proto), int(ttl), iseq, tcpflags,iack ])

con.execute('END TRANSACTION')
