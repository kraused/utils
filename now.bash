#!/bin/bash
# vi: tabstop=4:expandtab

# ISO 8601 conforming formats

FORMAT=( \
    "+%Y-%m-%d" \
    "+%Y%m%d" \
    "+%Y-W%V" \
    "+%Y-W%V" \
    "+%Y-W%V-%u" \
    "+%Y-%j" \
    "--utc +%Y-%m-%dT%H%M%SZ" \
    "+%Y-%m-%dT%H%M%SZ%z" )

if [[ "-f" == "$1" ]]; then
    exec date ${FORMAT[7]}
else
    exec date ${FORMAT[0]}
fi

