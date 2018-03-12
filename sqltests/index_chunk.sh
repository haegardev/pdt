#!/bin/bash
#Index a chunk of pcap files into dedicated indices per chunk
# find toindex/ -type f | sort | parallel -j 7 ./index_chunk.sh config {}

CONFIG=$1
CHUNK_FILENAME=$2

#Test some parameters
if [ -z "$CONFIG" ]; then
    echo "A config file must be specified" >&2
    exit 1
fi

. $CONFIG
ERR=$?
if [ $ERR -ne 0 ]; then
    echo "Could not load config file. Exit code: $ERR"
    exit 1
fi

if [ -z "$SENSOR" ]; then
    echo "A sensor name must be specified in config. SENSOR parameter" >&2
    exit 1
fi

if [ -z "$DATABASES" ]; then
    echo "Database directory must be set. DATABASES parameter" >&2
    exit 2
fi

 if [ ! -d "$DATABASES" ]; then
    echo "Database directory $DATABASES is not a directory" >&2
    exit 2
fi

if [ -z "$CHUNK_FILENAME" ]; then
    echo "A chunk must be specified"
    exit 1
fi

if [ ! -e "$CHUNK_FILENAME" ]; then
    echo "$CHUNK_FILENAME was not found"
    exit 1
fi
#Extend path with PDT software
export PATH=$PATH:$PDT
echo $PATH
FN=`basename $CHUNK_FILENAME`
IFN=`echo $FN | sed "s/chunk/db/g"`

#TODO add checks
DATE=`echo $FN | cut -d '.' -f 1`
YEAR=${DATE:0:4}
MONTH=${DATE:4:2}
DAY=${DATE:6:2}

IDD="$DATABASES/$SENSOR/$YEAR/$MONTH/$DAY"
if [ ! -d "$IDD" ]; then
    mkdir -p "$IDD"
fi
#Single write access for each database

for PCAPFILE in `cat $CHUNK_FILENAME`; do
    ADF="$IDD/$IFN"
    if [ -e "$ADF" ]; then
        e.sh $PCAPFILE | sqlindex.py --database "$IDD/$IFN" --filename $PCAPFILE
    else
        e.sh $PCAPFILE | sqlindex.py --database "$IDD/$IFN" --filename $PCAPFILE --create
    fi
done
