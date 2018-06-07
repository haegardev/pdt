#!/bin/bash
OUT="`ps aux | grep SCREEN | grep pdt_workers`"
if [ ! -z "$OUT" ]; then
    echo "At least a screen session for pdt workers are found from a previous run, abort" >&2
    exit 1
fi

screen -S pdt_workers -dm

sleep 1
for I in `seq 1 7`; do
    screen -S pdt_workers -X screen -t worker_$I sudo -u pdt /home/pdt/github/pdt/sqltests/sqlindex.py --worker --config /home/pdt/github/pdt/sqltests/config.cfg
    sleep 1
done
