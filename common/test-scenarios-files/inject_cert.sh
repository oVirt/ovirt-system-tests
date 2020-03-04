#!/bin/bash

# $0 grid_node_firefox engine /home/lago/ovirt-system-tests/deployment-basic-suite-master/current /home/lago/ovirt-system-tests/deployment-basic-suite-master/current/pki-resource

NAME=$1
FQDN=$2
PREFIX=$3
CA_PATH=$4
CERT_TAR=cert.tar
CERT_NEW_TAR=cert-new.tar
CERT_DIR=$PREFIX/cert

docker exec ${NAME} bash -c "tar cf /tmp/${CERT_TAR} \$(find /tmp -name cert9.db -o -name key4.db -o -name pkcs11.txt)"
docker cp ${NAME}:/tmp/${CERT_TAR} ${PREFIX}
mkdir -p ${CERT_DIR}
tar xv -C ${CERT_DIR} -f ${PREFIX}/${CERT_TAR}
certutil -A -n ${FQDN} -t "TCu,Cu,Tu" -i ${CA_PATH} -d sql:$(dirname `find ${CERT_DIR} -type f -print -quit`)
tar cfv ${PREFIX}/${CERT_NEW_TAR} -C ${CERT_DIR} .
docker cp ${PREFIX}/${CERT_NEW_TAR} ${NAME}:/tmp/${CERT_NEW_TAR}
docker exec ${NAME} tar xv --overwrite -f /tmp/${CERT_NEW_TAR} -C /tmp --strip 2
