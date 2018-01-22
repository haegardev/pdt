#!/usr/bin/python3
import gzip
import sys
import pprint
import redis
import os
import argparse

class ProcessWords:
    def __init__(self, minlen=4):
        self.words = dict()
        self.minlen = minlen
        self.dryrun = False

    def count_digits(self, hist):
        dcount = 0
        for ch in hist.keys():
            #Count digits
            if (ch >= 48 and ch <=57):
                dcount+=hist[ch]
        return dcount

    #skip characters such as < > etc
    def discard_na(self,hist):
        for ch in hist.keys():
            if ch < 63:
                #print ("DEBUG < 63")
                #allow some characters such as spaces and tabs
                if ch == 32 or ch == 9:
                    continue
                return True
            if ch >= 91 and ch <= 96:
                #print ("DEBUG  >= 91 and <=96")
                return True
            if ch >= 123 and ch <= 127:
                #print ("DEBUG > 123 and < 127")
                return True
        return False

    #Want at least n different characters
    def num_chars(self,hist):
        if len(hist.keys()) <=3:
            return True
        return False
  
    def compute_char_histo(self,line):
        out = dict()
        #Bytes are returned as ints
        for ch in line:
            if not ch in out:
                out[ch] = 0
            out[ch]+=1
        return out

    def process(self,filename):
        f = gzip.open(filename)
        for line in f.readlines():
            line = line[:-1]
            #Skip small words 
            if len(line) <= self.minlen:
                continue
            hist = self.compute_char_histo(line)
            #Focus on word subset of the ascii alphabet
            if self.discard_na(hist):
                continue
            if self.num_chars(hist):
                continue
            if line not in self.words:
                self.words[line] = 0
            self.words[line] += 1

    def dump_words(self):
        for w in self.words.keys():
            print (w)

    def index_redis(self,red, filename):
        key = filename
        for w in self.words:
            freq = self.words[w]
            red.zincrby(key,w,freq)

    def guess_day(self, filename):
        #Skip all file extensions based on ."
        u = filename.split(".")
        t = u[0].split("-")
        for i in t:
            try:
                num = int(i)
                if len(i) == 14:
                    i = i[0:8]
                    return i
            except ValueError as e:
                pass

    def inspect_redis_key(self,red,keyname):
        for (k,v) in red.zrevrange(keyname,0,-1, 'withscores'):
            if red.zscore("INSPECTED",k) is None:
                if len(k) <= self.minlen:
                    continue
                print (k.decode("ascii"))
        if self.dryrun == False:
            red.zunionstore("INSPECTED", [keyname])

    def remove_redis_key(self, red, keyname):
        for (k,v) in red.zrevrange(keyname, 0, -1, 'withscores'):
            red.zrem("INSPECTED", k)

    def reset_inspections(self,red):
        red.delete("INSPECTED")

parser = argparse.ArgumentParser(description="Process words")
parser.add_argument("--filename", type=str, nargs=1, required=False)
parser.add_argument("--socket", type=str)
parser.add_argument("--words", action='store_true')
parser.add_argument("--length",type=int,required = False)
parser.add_argument("--key", type=str, nargs=1, required = False)
parser.add_argument("--remove", action='store_true',required = False)
parser.add_argument("--reset", action='store_true', required = False)
parser.add_argument("--dry", action='store_true', required = False)

args = parser.parse_args()
obj = ProcessWords()
if args.length:
    obj.minlen = args.length 

if args.dry:
    obj.dryrun = True

if args.socket:
    red = redis.Redis(unix_socket_path=args.socket)
    if args.reset:
        obj.reset_inspections(red)
        sys.exit(1)
    if args.key:
        if args.remove:
            obj.remove_redis_key(red, args.key[0])
            sys.exit(0)
        obj.inspect_redis_key(red,args.key[0])
        sys.exit(0)
    fn = os.path.basename(args.filename[0])
    if red.sismember("WORDFILES", fn):
        sys.stderr.write("Processed already "+ fn + "\n")
        sys.exit(1)
    else:
        red.sadd("WORDFILES", fn)
    day = obj.guess_day(args.filename[0])

obj.process(args.filename[0])

if args.socket:
    obj.index_redis(red,day)

if args.words:
    obj.dump_words()
