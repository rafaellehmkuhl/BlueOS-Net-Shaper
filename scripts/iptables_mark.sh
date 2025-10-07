#!/bin/bash
# Usage: ./iptables_mark.sh <remote_ip> <port> <mark>
set -e
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 remote_ip port mark"
  exit 1
fi
REMOTE=$1
PORT=$2
MARK=$3

iptables -t mangle -A OUTPUT -p tcp -d $REMOTE --dport $PORT -j MARK --set-mark $MARK

echo "Marked traffic to $REMOTE:$PORT with mark $MARK"

