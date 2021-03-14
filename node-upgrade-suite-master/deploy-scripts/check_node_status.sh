#!/bin/bash
set -xe
nodectl check
echo 3 > /proc/sys/vm/drop_caches
