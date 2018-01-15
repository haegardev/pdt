#!/bin/bash
FILENAME=$1
if [ -z "$FILENAME" ]; then
    echo "A pcap file must be specified"
    exit 1
fi

tshark -n -T fields -E separator='|' -E occurrence=f  -o tcp.relative_sequence_numbers:FALSE  -e frame.number -e frame.time_epoch -e ip.proto -e ip.src -e udp.srcport -e tcp.srcport -e ip.dst -e udp.dstport -e tcp.dstport -e ip.ttl -e tcp.seq -e tcp.flags -e tcp.ack -r $FILENAME
