set -xe
DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')
ADDR=$(ip -4 addr show scope global up |grep -m1 inet | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}')

cat > /etc/yum.repos.d/local-ovirt.repo <<EOF
[alocalsync]
name=Latest oVirt nightly
baseurl=http://$ADDR:8585/default/$DIST/
enabled=1
gpgcheck=0
repo_gpgcheck=0
cost=1
keepcache=1
ip_resolve=4
max_connections=10
deltarpm=0
EOF


# disable any other repos to avoid downloading metadata
yum install --disablerepo=\* --enablerepo=alocalsync -y yum-utils
yum-config-manager --disable \*
yum-config-manager --enable alocalsync
