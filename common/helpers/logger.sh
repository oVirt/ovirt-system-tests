#!/bin/bash

# Helper functions for logging

logger.log() {
    # $1: Level
    # $>1: Msg
    (
        set +x

        local DEFAULT='\x1b[0m'
        local RED='\x1b[31m'
        local GREEN='\x1b[32m'
        local YELLOW='\x1b[33m'
        local BLUE='\x1b[34m'

        local ERROR="$RED"
        local WARNING="$YELLOW"
        local INFO="$BLUE"
        local SUCCESS="$GREEN"

        local calling_script="$(basename "$0")"
        local calling_func="${FUNCNAME[2]}"
        local level="${1:?}"
        local timestamp=$(date "+%Y-%m-%d %H:%M:%S.%N%z")

        shift

        printf \
            "%b%s %s::%s::%s:: %s%b\n" \
            "${!level}" \
            "$timestamp" \
            "$calling_script" \
            "$calling_func" \
            "${level}" \
            "$*" \
            "$DEFAULT"
    )
}

logger.info() {
    logger.log INFO "$@"
}

logger.error() {
    logger.log ERROR "$@"
}

logger.warning() {
    logger.log WARNING "$@"
}

logger.success() {
    logger.log SUCCESS "$@"
}
