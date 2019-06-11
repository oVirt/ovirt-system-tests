#!/usr/bin/bash

PLUGIN_FILE="/usr/lib/python2.7/site-packages/sos/plugins/vdsm.py"

if [ ! -f ${PLUGIN_FILE} ]; then
  cp $(dirname $0)/vdsm.py ${PLUGIN_FILE}
  chown root:root ${PLUGIN_FILE}
  chmod 644 ${PLUGIN_FILE}
fi
