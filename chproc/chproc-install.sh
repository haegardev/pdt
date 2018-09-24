#!/bin/bash
#
# Helper scripts for setting up processing chain
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

NAME=$1
HOST=$2
PORT=$3
REDISURL="http://download.redis.io/releases/redis-4.0.11.tar.gz"

if [ -z $PORT ]; then
    echo "A port for the redis server should be configured." >&2
    exit 1
fi

if [ -z "$HOST" ]; then
    echo "A host where redis listens should be configured,"  >&2
    exit 1
fi

declare -a programs=("mkpasswd")
declare -a directories=("exports" "cveexport" "bin" "etc" "current_pcaps" "databases" "var/pids" "build")



#Test if necessary programs are installed
for i in "${programs[@]}"; do
    if [ -z "`which $i`" ]; then
        echo "Necessary program $i not found. Do nothing." >&2
        exit 1
    fi
done


if [ -z "$NAME" ]; then
    echo "A name must be specified. Do noththing." >&2
    exit 1
fi

if [  `id -u` != 0 ]; then
    echo "Script should be executed as root"
    exit 1
fi

ROOT="/home/$NAME"
DOC="$ROOT/install.txt"

#Create user if not exists
if [ ! -d $ROOT ]; then
    SALT=`head -c 8 /dev/urandom  | sha1sum  | cut -d ' ' -f1`
    PASSWD=`mkpasswd $SALT`
    useradd -m -p $PASSWD -s /bin/bash $NAME
    if [ $? -ne 0 ]; then
        echo "User creation failed. Abort." >&2
        exit 1
    fi
    echo "Installation notes" >> $DOC
    echo "==================" >> $DOC
    echo "Installed on: `date +%Y%m%d%H%M`" >>$DOC
    echo "Username: $NAME" >> $DOC
    echo "Password: $PASSWD" >>$DOC
fi
#Create directory
for i in "${directories[@]}"; do
    d="$ROOT/$i"
    if [ ! -d "$d" ]; then
        mkdir -p "$d"
        chown $NAME:$NAME $d
    fi
done

#Check if redis is there
if [ ! -e "$ROOT/bin/redis-server" ]; then
    wget $REDISURL -O "$ROOT/build/redis.tar.gz"
    if [ $? -ne 0 ]; then
        echo "Could not download redis. Abort."
        exit 1
    fi
    chown $NAME:$NAME "$ROOT/build/redis.tar.gz"
    #Build redis
    cd "$ROOT/build"
    tar -zxf "$ROOT/build/redis.tar.gz"
    if [ $? -ne 0 ]; then
        echo "Could extract redis. Abort." >&2
        exit 1
    fi
    #Use the first directory and hope it is the good one
    for d in `ls "$ROOT/build/"`; do
        if [ -d "$d" ]; then
            REDDIR="$ROOT/build/$d"
            cd "$REDDIR"
            make
            if [ $? -ne 0 ]; then
                echo "Redis build failed.abort." >&2
                exit 1
            fi
            cp "$REDDIR/src/redis-cli" "$ROOT/bin"
            if [ $? -ne 0 ]; then
                echo "Redis client was not found" >&2
                exit 1
            fi
            cp "$REDDIR/src/redis-server" "$ROOT/bin"
            if [ $? -ne 0 ]; then
                echo "Redis-server was not found" >&2
                exit 1
            fi
        fi
    done
    #Update configuration file
    cat $REDDIR/redis.conf | sed "s/^port 6379/port 1234/g" \
    | sed "s/^save /#save/g"\
    | sed "s#^dir ./#dir $ROOT/databases#g"\
    | sed "s/^bind 127.0.0.1/bind $HOST/g"\
    | sed "s/^daemonize no/daemonize yes/g"\
    | sed "s#pidfile /var/run/redis_6379.pid#pidfile $ROOT/var/pids/redis.pid#g"\
    | sed "s/# syslog-enabled no/syslog-enabled yes/g"\
    > $ROOT/etc/redis.conf
    chown $NAME:$NAME "$ROOT/etc/redis.conf"
    #Try to start redis
    sudo -u $NAME $ROOT/bin/redis-server $ROOT/etc/redis.conf
    if [ $? -ne 0 ]; then
        echo "Failed to start redis" >&2
        exit 1
    fi
fi
