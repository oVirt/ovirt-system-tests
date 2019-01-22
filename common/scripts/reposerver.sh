#!/bin/bash -ex

# exec {fd}<> lock-file

main() {
    local root="$1"
    local lock_file="$2"
    local out_file="$3"
    local id
    shift 3 || :

    [[ ! ("$root" && "$lock_file" && "$out_file") ]] && usage && exit 1

    close_fds

    id=$(
        docker run \
            -v "${root}:/usr/share/nginx/html:ro" \
            -d \
            "$@" \
            nginx:1.15.8-alpine
    )
    docker inspect "$id" --format '{{.NetworkSettings.IPAddress}}' > "$out_file"

    flock "$lock_file" echo "Shutting down server..."
    docker stop "$id"
    echo "Server is down"
}


usage() {
    echo "
Usage: $0 <path-to-serve> <lock-file> <out-file>

<path-to-serve> Which path the server should serve
<lock-file> The server will serve content until Flock on this file isn't locked
<out-file> Write the servers ip to this file.
"
}


close_fds() {
    # Close non-default fd
    # Needed in order to not hold the lock that we got from the parent process
    for fd in $(ls /proc/$$/fd); do
      case "$fd" in
        0|1|2|255)
          ;;
        *)
          eval "exec $fd>&-"
          ;;
      esac
    done
}

[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"
