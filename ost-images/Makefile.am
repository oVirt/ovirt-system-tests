# This speeds up dist
GZIP_ENV := "--fast"

# This can be overriden by running with 'make DISTRO=...'
DISTRO := el8

# Accepts both ISOs and repo urls, can be overriden by running with 'make INSTALL_URL=...'
INSTALL_URL := "http://isoredirect.centos.org/centos/8/isos/x86_64/CentOS-8.1.1911-x86_64-dvd1.iso"

# The url of root of repos, can be overriden by running with 'make REPO_ROOT=...'
REPO_ROOT := "http://mirror.centos.org/centos/8/"

# Empty string when using repo-based installs, ".iso" otherwise
_USING_ISO := $(findstring .iso,$(INSTALL_URL))

# Whether to build the base image or not. For repo-based installation always
# set to "yes". For iso-based installations looks for installed base package
# and if finds one, base won't be built. Can be overriden by running
# with 'make BUILD_BASE=...'. Any non-empty string will be treated as true
# and an empty string is treated as false.
BUILD_BASE := $(if $(_USING_ISO),$(findstring not installed,$(shell rpm -q $(PACKAGE_NAME)-$(DISTRO)-base)),yes)

# Use either the base image that's built locally
# or the one that's already installed
_BASE_IMAGE_PREFIX := $(if $(BUILD_BASE),,$(shell rpm -q --queryformat '%{INSTPREFIXES}' $(PACKAGE_NAME)-$(DISTRO)-base)/$(PACKAGE_NAME)/)

# Whether to build a real upgrade layer. Upgrade layer doesn't really make
# sense in scenarios where you build from nightly repos.
# Can be overriden by running with 'make DUMMY_UPGRADE=...'. Any non-empty
# string will be treated as true and an empty string as false.
DUMMY_UPGRADE := $(if $(_USING_ISO),,yes)

# These variables point to scripts that provision "engine-installed"
# and "host-installed" layers. Can be overriden by running with i.e. 'make PROVISION_HOST_SCRIPT=...'
PROVISION_ENGINE_SCRIPT := $(DISTRO)-provision-engine.sh.in
PROVISION_HOST_SCRIPT := $(DISTRO)-provision-host.sh.in

# This resolves to either smth like 'el8.iso' for ISOs or url for repository urls
_LOCATION := $(if $(_USING_ISO),$(DISTRO).iso,$(INSTALL_URL))

# Where pkglist.txt files are put
_PKGLIST_PATH := /var/tmp

# Command used to make *pkglist-diff.txt files
_DIFF := -diff --new-line-format="" --unchanged-line-format=""

# If the INSTALL_URL is an iso image then download it
# (or make a symlink to it if it's a local path) first.
%.iso:
	$(if $(findstring http,$(INSTALL_URL)),curl -L -o $@ $(INSTALL_URL),ln -s $(INSTALL_URL) $@)

%.ks: template.ks.in
	sed "s|%REPO_ROOT%|$(REPO_ROOT)|" template.ks.in > $@

%-base.qcow2: $(if $(_USING_ISO), %.iso) %.ks
	qemu-img create -f qcow2 $@.tmp 12G
#	Qemu runs with lowered privileges so if the build
#	is done by root, the image is created with 664
#	permissions and qemu is unable to write to it.
#	This is fixed on RPM level.
	chmod 666 $@.tmp
	virt-install \
		--name $(@:.qcow2=) \
		--memory 2048 \
		--vcpus 2 \
		--disk path=$@.tmp \
		--location=$(_LOCATION) \
		--os-variant rhel8-unknown \
		--hvm \
		--graphics=vnc \
		--initrd-inject=$*.ks \
		--extra-args ks=file:/$*.ks \
		--noautoconsole \
		--wait 30 \
		--noreboot
	virt-customize \
		-a $@.tmp \
		--run-command "rpm -qa | sort > $(_PKGLIST_PATH)/$(@:.qcow2=-pkglist.txt)"
	mv $@.tmp $@

%-upgrade.qcow2: $(if $(BUILD_BASE),%-base.qcow2)
	qemu-img create -f qcow2 -F qcow2 -b $(_BASE_IMAGE_PREFIX)$(*)-base.qcow2 $@.tmp
#	See the remark above about chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		$(if $(DUMMY_UPGRADE),, --run-command "dnf upgrade -y") \
		--run-command "dnf clean all" \
		--run-command "rpm -qa | sort > $(_PKGLIST_PATH)/$(@:.qcow2=-pkglist.txt)" \
		--selinux-relabel
	mv $@.tmp $@

%-provision-engine.sh:
	cp $(PROVISION_ENGINE_SCRIPT) $@

%-engine-installed.qcow2: %-upgrade.qcow2 %-provision-engine.sh
	qemu-img create -f qcow2 -F qcow2 -b $*-upgrade.qcow2 $@.tmp
#	See the remark above about chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		--run "$*-provision-engine.sh" \
		--run-command "rpm -qa | sort > $(_PKGLIST_PATH)/$(@:.qcow2=-pkglist.txt)" \
		--selinux-relabel
	mv $@.tmp $@

%-provision-host.sh:
	cp $(PROVISION_HOST_SCRIPT) $@

%-host-installed.qcow2: %-upgrade.qcow2 %-provision-host.sh
	qemu-img create -f qcow2 -F qcow2 -b $*-upgrade.qcow2 $@.tmp
#	See the remark above aboud chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		--run "$*-provision-host.sh" \
		--run-command "rpm -qa | sort > $(_PKGLIST_PATH)/$(@:.qcow2=-pkglist.txt)" \
		--selinux-relabel
	mv $@.tmp $@

%-pkglist.txt: %.qcow2
	virt-copy-out -a $*.qcow2 $(_PKGLIST_PATH)/$@ .

%-upgrade-pkglist-diff.txt: %-upgrade-pkglist.txt $(if $(BUILD_BASE),%-base-pkglist.txt)
	$(_DIFF) $*-upgrade-pkglist.txt $(_BASE_IMAGE_PREFIX)$*-base-pkglist.txt > $@

%-host-installed-pkglist-diff.txt: %-host-installed-pkglist.txt %-upgrade-pkglist.txt
	$(_DIFF) $*-host-installed-pkglist.txt $*-upgrade-pkglist.txt > $@

%-engine-installed-pkglist-diff.txt: %-engine-installed-pkglist.txt %-upgrade-pkglist.txt
	$(_DIFF) $*-engine-installed-pkglist.txt $*-upgrade-pkglist.txt > $@

ost-images.spec: ost-images.spec.in
	sed 's/[@]PACKAGE_RELEASE[@]/$(PACKAGE_RELEASE)/g' $< >$@

ks: $(DISTRO).ks

.INTERMEDIATE: $(DISTRO).iso

iso: $(DISTRO).iso

base: $(DISTRO)-base.qcow2 $(DISTRO)-base-pkglist.txt

upgrade: $(DISTRO)-upgrade.qcow2 $(DISTRO)-upgrade-pkglist.txt $(DISTRO)-upgrade-pkglist-diff.txt

engine: $(DISTRO)-engine-installed.qcow2 $(DISTRO)-engine-installed-pkglist.txt $(DISTRO)-engine-installed-pkglist-diff.txt

host: $(DISTRO)-host-installed.qcow2 $(DISTRO)-host-installed-pkglist.txt $(DISTRO)-host-installed-pkglist-diff.txt

spec: ost-images.spec

all: $(if $(BUILD_BASE),base) upgrade engine host spec

gen-VERSION:
	if test -d ../.git; then                                             \
		$(top_srcdir)/build-aux/pkg-version --full > $(distdir)/VERSION; \
	fi

dist-hook: gen-VERSION

clean-local:
	-virsh destroy $(DISTRO)-base
	-virsh undefine $(DISTRO)-base

dist_image_DATA = \
	$(if $(BUILD_BASE),$(DISTRO)-base-pkglist.txt) \
	$(if $(BUILD_BASE),$(DISTRO)-base.qcow2) \
	$(if $(BUILD_BASE),$(DISTRO).ks) \
	$(DISTRO)-engine-installed-pkglist-diff.txt \
	$(DISTRO)-engine-installed-pkglist.txt \
	$(DISTRO)-engine-installed.qcow2 \
	$(DISTRO)-host-installed-pkglist-diff.txt \
	$(DISTRO)-host-installed-pkglist.txt \
	$(DISTRO)-host-installed.qcow2 \
	$(DISTRO)-upgrade-pkglist-diff.txt \
	$(DISTRO)-upgrade-pkglist.txt \
	$(DISTRO)-upgrade.qcow2 \
	$(NULL)

dist_image_SCRIPTS = \
	$(DISTRO)-provision-engine.sh \
	$(DISTRO)-provision-host.sh \
	$(NULL)

CLEANFILES = \
	*-pkglist*.txt \
	*.ks \
	*.qcow2 \
	*.qcow2.tmp \
	*.spec \
	$(DISTRO)-provision-engine.sh \
	$(DISTRO)-provision-host.sh \
	$(DIST_ARCHIVES) \
	$(NULL)

EXTRA_DIST = \
	ost-images.spec \
	ost-images.spec.in \
	template.ks.in \
	$(NULL)

rpm: spec
	rpmbuild -bb \
		--define "distro $(DISTRO)" \
		--define "release $(PACKAGE_RELEASE)" \
		--define "with_base $(if $(BUILD_BASE),1,0)" \
		--define "dummy_upgrade $(if $(DUMMY_UPGRADE),1,0)" \
		--build-in-place \
		ost-images.spec
