#!/usr/bin/python3
import argparse
import sys
import os

parser = argparse.ArgumentParser(description='Group filenames per day')
parser.add_argument('--dest', type=str, required=True, nargs=1, help='Directory for storing the files')
args = parser.parse_args()
dest = args.dest[0]


filehandles = dict()
for line in sys.stdin.readlines():
    line = line[:-1]
    filename = os.path.basename(line)
    t = filename.split('.')
    t.pop()
    filename = ".".join(t)
    if "-" in filename:
        t = filename.split("-")
        filename = t[1]
    filename = dest + os.sep + filename[0:8] +".txt"
    if filename not in filehandles:
        filehandles[filename] = open(filename, "w")
    filehandles[filename].write(line+"\n")


