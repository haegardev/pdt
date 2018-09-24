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
NAME="$ROOT/chproc-extract.sh"

PIDFILE="$ROOT/var/pids/chproc-extract.pid"

declare -a directories=("exports" "cveexport" "bin" "etc" "current_pcaps" "var/pids")


if [ -z "$ROOT" ]; then
    logger -t $NAME "No root directory was executed."
    exit 1
fi

for i in "${directories[@]}"; do
    d="$ROOT/$i"
    if [ ! -d "$d" ]; then
        logger -t $NAME  "Directory $d is not there. abort"
        exit 1
    fi
done


if [ -e "$PIDFILE" ]; then
    logger -t $NAME "Annother instance is running, abort"
    exit 1
fi

echo $$ > $PIDFILE
rm $PIDFILE
#Record pid file to avoid concurrent processing

