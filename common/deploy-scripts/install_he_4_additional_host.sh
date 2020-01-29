fstrim -va
yum install -y ovirt-hosted-engine-setup
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "yum install failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/* /var/cache/dnf/*
fstrim -va
echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
