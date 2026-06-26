#!/bin/sh

DB_INIT="DB_INIT"
if [ ! -e /$DB_INIT ]; then
    python3 init.py || exit 1
    touch /$DB_INIT
fi

exec "$@"