# This speeds up dist
GZIP_ENV := "--fast"

# This can be overriden by running with 'make DISTRO=...'
DISTRO := el8

# Accepts both ISOs and repo urls, can be overriden by running with 'make INSTALL_URL=...'
INSTALL_URL := "http://isoredirect.centos.org/centos/8/isos/x86_64/CentOS-8.1.1911-x86_64-dvd1.iso"

# The url of root of repos, can be overriden by running with 'make REPO_ROOT=...'
REPO_ROOT := "http://mirror.centos.org/centos/8/"

# Whether to build the base image or not. Looks for installed base package
# and if finds one, base won't be built. Can be overriden by running
# with 'make BUILD_BASE=...'. Any non-empty string will be treated as true
# and an empty string is treated as false.
BUILD_BASE := $(findstring not installed,$(shell rpm -q $(PACKAGE_NAME)-$(DISTRO)-base))

# Use either the base image that's built locally
# or the one that's already installed
_BASE_IMAGE_PREFIX := $(if $(BUILD_BASE),,$(imagedir)/)

# Empty string when using repo-based installs, ".iso" otherwise
_USING_ISO := $(findstring .iso,$(INSTALL_URL))

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


# If the INSTALL_URL is an iso image then download it first.
%.iso:
	curl -L -o $@ $(INSTALL_URL)

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
	mv $@.tmp $@

%-upgrade.qcow2: $(if $(BUILD_BASE),%-base.qcow2)
	qemu-img create -f qcow2 -b $(_BASE_IMAGE_PREFIX)$(*)-base.qcow2 $@.tmp
#	See the remark above about chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		$(if $(DUMMY_UPGRADE),, --run-command "dnf upgrade -y") \
		--run-command "dnf clean all" \
		--selinux-relabel
	mv $@.tmp $@

%-provision-engine.sh:
	cp $(PROVISION_ENGINE_SCRIPT) $@

%-engine-installed.qcow2: %-upgrade.qcow2 %-provision-engine.sh
	qemu-img create -f qcow2 -b $*-upgrade.qcow2 $@.tmp
#	See the remark above about chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		--run "$*-provision-engine.sh" \
		--selinux-relabel
	mv $@.tmp $@

%-provision-host.sh:
	cp $(PROVISION_HOST_SCRIPT) $@

%-host-installed.qcow2: %-upgrade.qcow2 %-provision-host.sh
	qemu-img create -f qcow2 -b $*-upgrade.qcow2 $@.tmp
#	See the remark above aboud chmod.
	chmod 666 $@.tmp
	virt-customize \
		-a $@.tmp \
		--run "$*-provision-host.sh" \
		--selinux-relabel
	mv $@.tmp $@

ost-images.spec: ost-images.spec.in
	sed 's/[@]PACKAGE_RELEASE[@]/$(PACKAGE_RELEASE)/g' $< >$@

ks: $(DISTRO).ks

.INTERMEDIATE: $(DISTRO).iso

iso: $(DISTRO).iso

base: $(DISTRO)-base.qcow2

upgrade: $(DISTRO)-upgrade.qcow2

engine: $(DISTRO)-engine-installed.qcow2

host: $(DISTRO)-host-installed.qcow2

spec: ost-images.spec

all: $(if $(BUILD_BASE),base) upgrade engine host spec

# While qemu is fine with having relative paths
# for backing images, lago is not. This is why we need
# to rebase the images to paths where the backing
# image lands after installation.
.PHONY: rebase-images
rebase-images:
	echo "rebasing"
	qemu-img rebase -u -b "$(imagedir)/$(DISTRO)-base.qcow2" "$(distdir)/$(DISTRO)-upgrade.qcow2"
	qemu-img rebase -u -b "$(imagedir)/$(DISTRO)-upgrade.qcow2" "$(distdir)/$(DISTRO)-host-installed.qcow2"
	qemu-img rebase -u -b "$(imagedir)/$(DISTRO)-upgrade.qcow2" "$(distdir)/$(DISTRO)-engine-installed.qcow2"

gen-VERSION:
	if test -d ../.git; then                                             \
		$(top_srcdir)/build-aux/pkg-version --full > $(distdir)/VERSION; \
	fi

dist-hook: gen-VERSION rebase-images

clean-local:
	-virsh destroy $(DISTRO)-base
	-virsh undefine $(DISTRO)-base

dist_image_DATA = \
	$(if $(BUILD_BASE),$(DISTRO)-base.qcow2) \
	$(if $(BUILD_BASE),$(DISTRO).ks) \
	$(DISTRO)-engine-installed.qcow2 \
	$(DISTRO)-host-installed.qcow2 \
	$(DISTRO)-upgrade.qcow2 \
	$(NULL)

dist_image_SCRIPTS = \
	$(if $(BUILD_BASE),rebase_images.sh) \
	$(DISTRO)-provision-engine.sh \
	$(DISTRO)-provision-host.sh \
	$(NULL)

CLEANFILES = \
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

srpm: dist
	rpmbuild -ts \
		--define "distro $(DISTRO)" \
		--define "release $(PACKAGE_RELEASE)" \
		--define "with_base $(if $(BUILD_BASE),1,0)" \
		--define "dummy_upgrade $(if $(DUMMY_UPGRADE),1,0)" \
		$(DIST_ARCHIVES)

rpm: dist
	rpmbuild -tb \
		--define "distro $(DISTRO)" \
		--define "release $(PACKAGE_RELEASE)" \
		--define "with_base $(if $(BUILD_BASE),1,0)" \
		--define "dummy_upgrade $(if $(DUMMY_UPGRADE),1,0)" \
		$(DIST_ARCHIVES)
