#!/bin/bash

PATHS=`find -L . -path ./exported-artifacts -prune -o -path ./custom-ost-images -prune -o -type l -print`

if [ -n "$PATHS" ]; then
    echo "Found broken symlinks in the repository:"
    echo "$PATHS"
    exit 1;
fi
