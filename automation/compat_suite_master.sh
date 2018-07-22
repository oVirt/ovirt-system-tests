#!/bin/bash -ex
export OST_DC_VERSION="$(echo $(basename $0) | tr - _ | awk -F _ '{print $2}')"
source "$(dirname $0)/suite.sh"
