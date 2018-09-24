#!/bin/bash
#
# Helper scripts for preprocessing up processing chain
#
# Copyright (C) 2018 Gerard Wagener
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

ROOT=$1
HOST=$2
PORT=$3
FILEQUEUE=$4

NAME="$ROOT/chproc-extract.sh"

PIDFILE="$ROOT/var/pids/chproc-extract.pid"

declare -a directories=("exports" "cveexport" "bin" "etc" "current_pcaps" "var/pids")
declare -a programs=("tcprewrite" "tshark")
declare -a cprograms=("$ROOT/bin/redis-cli")


if [ -z "$ROOT" ]; then
    logger -t $NAME "No root directory was executed."
    exit 1
fi

if [ -z "$HOST" ]; then
    logger -t $NAME "A redis host must be specified."
    exit 1
fi

if [ -z "$PORT" ]; then
    logger -t $NAME "A port must be configured."
    exit 1
fi

if [ -z "$FILEQUEUE" ]; then
    logger -t $NAME "A queue must be configured."
    exit 1
fi

for i in "${directories[@]}"; do
    d="$ROOT/$i"
    if [ ! -d "$d" ]; then
        logger -t $NAME  "Directory $d is not there. abort"
        exit 1
    fi
done

#Check if mandatory programs are there
for i in "${programs[@]}"; do
    if [ -z "`which $i`" ]; then
        echo "Necessary program $i not found. Do nothing." >&2
        exit 1
    fi
done

if [ -e "$PIDFILE" ]; then
    logger -t $NAME "Annother instance is running, abort"
    exit 1
fi

#Record pid file to avoid concurrent processing
echo $$ > $PIDFILE

#Check if custom programs are there
for i in "${cprograms[@]}"; do
    if [ ! -e $i ]; then
        logger -t $NAME  "Custom program: $i not found.Abort."
        exit 1
    fi
done

#Go through the queue and preprocess the files

while [ 1 ]; do
    FILENAME="`$ROOT/bin/redis-cli -p $PORT -h $HOST lpop $FILEQUEUE`"
    if [ -z "$FILENAME" ]; then
        break
    fi
    if [ ! -e $FILENAME ]; then
        logger -t $NAME "$FILENAME was not found"
        continue
    fi
done

rm $PIDFILE

