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

declare -a programs=("mkpasswd")
declare -a directories=("exports" "cveexport" "bin")

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
