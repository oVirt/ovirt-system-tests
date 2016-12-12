fstrim -va
yum install -y iptables
yum install -y ovirt-hosted-engine-setup ovirt-engine-appliance
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "yum install failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /dev/shm/*.rpm
fstrim -va

echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
