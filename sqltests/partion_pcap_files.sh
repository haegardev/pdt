#!/bin/bash
#Create file lists of pcaps that should be indexed in a single index file
#These files can be procesed with the following command
#
# find toindex/ -type f | sort | parallel -j 7 ./index_chunk.sh config {}
#

CONFIG="$1"

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

if [ -z "$NSHARDS" ]; then
    echo "The number of shards is missing in the config. NSHARDS parameters." >&2
    exit 2
fi

#TODO test if number

if [ -z "$YEAR" ]; then
    echo "The year of the data set is missing. YEAR parameter." >&2
    exit 2
fi

if [ -z "$MAXFILES" ]; then
    echo "The expected maximal number of files per day is missing. MAXFILES parameter." >&2
    exit 2
fi

if [ -z "$SENSOR" ]; then
    echo "A sensor name is missing. SENSOR parameter." >&2
    exit 2
fi

if [ -z "$DATA" ]; then
    echo "A directory containing the pcaps is missing. DATA parameter" >&2
    exit 2
fi

if [ -z "$RESDIR" ]; then
    echo "A result directory containing the filelist chunks are missing. RESDIR parameter" >&2
    exit 2
fi

if [ ! -d "$RESDIR" ]; then
    echo "$RESDIR is not a directory" >&2
    exit 2
fi

ROOT="$DATA/$SENSOR/files/$YEAR"
RESULT="$RESDIR/toindex/$SENSOR"

if [ ! -d $ROOT ]; then
    echo "Encountered invalid pcap directory structure" >&2
    exit 3
fi

let FILES_SHARD="$MAXFILES / $NSHARDS"
for MONTH in `ls $ROOT`; do
    D="$ROOT/$MONTH"
    if [ -d "$D" ]; then
        for DAY in `ls $D`; do
            TD="$RESULT/$YEAR/$MONTH/$DAY"
            if [ ! -d "$TD" ]; then
                mkdir -p $TD
            fi
            CD="$D/$DAY"
            TF="$TD/$YEAR$MONTH$DAY.filelist"
            find $CD -type f |  sort  > $TF
            split -l $FILES_SHARD -d $TF "$TD/$YEAR$MONTH$DAY.chunk."
            rm $TF
        done
    fi
done
