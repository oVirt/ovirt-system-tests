set -xe

cat > /root/iso-uploader.conf << EOF
[ISOUploader]
user=admin@internal
passwd=123
engine=localhost:443
EOF

# engine 4 resolves its FQDN
ADDR=$(/sbin/ip -4 -o addr show dev eth0 | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1}')
echo "$ADDR engine" >> /etc/hosts

yum install -y deltarpm
yum install --nogpgcheck -y ovirt-engine


# Enable debug logs on the engine
sed -i \
    -e '/.*logger category="org.ovirt"/{ n; s/INFO/DEBUG/ }' \
    -e '/.*<root-logger>/{ n; s/INFO/DEBUG/ }' \
    /usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in
