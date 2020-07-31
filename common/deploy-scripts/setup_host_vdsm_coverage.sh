#!/bin/bash -xe

# Need redundancy here - shebang line is ignored when ran through ssh
set -ex

if [[ -x /usr/bin/dnf ]]; then
    DNF=dnf
else
    DNF=yum
fi

if grep -qe '\(Red Hat\|CentOS\).*release 7' /etc/redhat-release; then
    PYTHON_VERSION=""
else
    PYTHON_VERSION="3"
fi

if ! rpm -q python${PYTHON_VERSION}-coverage > /dev/null; then
    $DNF install -y python${PYTHON_VERSION}-coverage
fi

VDSM_CONF_DIR="/etc/vdsm/vdsm.conf.d"
VDSM_COVERAGE_CONF="${VDSM_CONF_DIR}/coverage.conf"

mkdir -p "${VDSM_CONF_DIR}"

cat > "${VDSM_COVERAGE_CONF}" << EOF
[devel]
coverage_enable = true
EOF

COVERAGE_DIR="/var/lib/vdsm/coverage"
COVERAGE_RC="${COVERAGE_DIR}/coveragerc"
COVERAGE_DATA="${COVERAGE_DIR}/vdsm.coverage"

mkdir -p "${COVERAGE_DIR}"
chmod 777 "${COVERAGE_DIR}"

cat > "${COVERAGE_RC}" << EOF
[run]
branch = True
concurrency = thread multiprocessing
parallel = True
data_file = ${COVERAGE_DATA}
source = vdsm, yajsonrpc
EOF

echo "COVERAGE_PROCESS_START=\"${COVERAGE_RC}\"" >> /etc/sysconfig/vdsm
echo "COVERAGE_PROCESS_START=\"${COVERAGE_RC}\"" >> /etc/sysconfig/supervdsmd
