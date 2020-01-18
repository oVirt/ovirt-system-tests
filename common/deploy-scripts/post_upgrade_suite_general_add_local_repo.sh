set -xe

DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')
ADDR=$(ip -4 addr show scope global up |grep -m1 inet | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}')
curl_res=0
curl -f http://$ADDR:8585/default/${DIST%_*}/repodata/repomd.xml  || curl_res=$?

if [[ "$curl_res" -eq 0 ]]; then
    cat > /etc/yum.repos.d/local-ovirt.repo <<EOF
[alocalsync]
name=Reposync & Extra Sources Content
baseurl=http://$ADDR:8585/default/${DIST%_*}/
enabled=1
gpgcheck=0
repo_gpgcheck=0
cost=1
keepcache=1
ip_resolve=4
max_connections=10
deltarpm=0
priority=1
EOF

fi

sed -i "s/var\/cache/dev\/shm/g" /etc/yum.conf
echo "persistdir=/dev/shm" >> /etc/yum.conf


# disable any other repos to avoid downloading metadata
cd  /etc/yum.repos.d/
yum install --disablerepo=\* --enablerepo="$(cat reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main | xargs | tr ' ' ',')" -y yum-utils
yum-config-manager --disable \*

for i in $(cat reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main); do
    yum-config-manager --enable "$i"
done

INSTALL_PKG=("tar")

python="$(command -v python)" || res=$?
[[ "$res" -ne 0 ]] && {
    INSTALL_PKG+=("python3")
    INSTALL_PKG+=("wget")
}
yum install -y "${INSTALL_PKG[@]}"

[[ "$curl_res" -eq 0 ]] && {
    yum-config-manager --enable alocalsync
}

yum repolist -v > /var/log/rst_yum_repos.log
