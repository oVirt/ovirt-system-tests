#!/bin/bash

help() {
echo "
$0 command [arguments]

run <suite> <distro> [<pytest args>...]
    initializes the workspace with preinstalled distro ost-images, launches VMs and runs the whole suite
    add extra repos with --custom-repo=url
    skip check that extra repo is actually used with --skip-custom-repos-check
status
    show environment status, VM details
shell <host> [command ...]
    opens ssh connection
console <host>
    opens virsh console
destroy
    stop and remove the running environment
"
exit 0
}

[[ $# -eq 0 ]] && help
source lagofy.sh
cmd=$1; shift
case "$cmd" in
  run)
    suite=$1; shift
    distro=$2; shift
    ost_init $suite $distro || exit 1
    ost_run_tests $@
    ;;
  status)
    ost_status
    ;;
  destroy)
    ost_destroy
    ;;
  console)
    host=$1; shift;
    ost_console $host $@
    ;;
  shell)
    host=$1; shift;
    ost_shell $host $@
    ;;
  *)
    echo unknown command \"$cmd\"
    help
    ;;
  esac
exit 0

