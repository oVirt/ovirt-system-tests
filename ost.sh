#!/bin/bash

help() {
echo "
$0 command [arguments]

run [-4|-6] [--ost-coverage] <suite> <distro> [<pytest args>...]
    initializes the workspace with preinstalled distro ost-images, launches VMs and runs the whole suite
    add extra repos with --custom-repo=url
    skip check that extra repo is actually used with --skip-custom-repos-check
status
    show environment status, VM details
shell <host> [command ...]
    opens ssh connection
console <host>
    opens virsh console
fetch-artifacts
    fetches artifacts from all hosts
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
    [[ "$1" =~ ^-4$|^-6$ ]] && { ipv=$1; shift; }
    [[ "$1" == "--ost-coverage" ]] && { ost_coverage_flag=$1; shift; }
    suite=$1; shift
    distro=$1; shift
    ost_init $ipv $suite $distro || exit 1
    ost_run_tests $ost_coverage_flag $@ || exit 1
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
  fetch-artifacts)
    ost_fetch_artifacts
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

