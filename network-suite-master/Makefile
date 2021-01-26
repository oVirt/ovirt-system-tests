NAME=ovirtlib
VERSION=0.0.1
DIST_DIR=$(NAME)-$(VERSION)
GITHASH=$(shell git rev-parse --short HEAD)
TIMESTAMP:=$(shell date +'%Y%m%d%H%M%S')
RELEASE_SUFFIX=0.$(TIMESTAMP).git$(GITHASH)
TARBALL=$(NAME)-$(VERSION).tar.gz
SPEC=$(NAME).spec
PYTHON=python3

GENERATED = ovirtlib/version.py \
	    $(SPEC) \
	    $(NULL)

$(GENERATED) : % : %.in
	sed \
	    -e s/@NAME@/$(NAME)/ \
	    -e s/@RELEASE_SUFFIX@/$(RELEASE_SUFFIX)/ \
	    -e s/@TIMESTAMP@/$(TIMESTAMP)/ \
	    -e s/@TARBALL@/$(TARBALL)/ \
	    -e s/@VERSION@/$(VERSION)/ \
	    < $<  > $@

clean:
	$(PYTHON) ovirtlib_setup.py clean --all || :
	rm -fr \
	    $(GENERATED) \
	    build \
	    $(TARBALL) \
	    $(NULL)

.PHONY: dist
dist: all
	mkdir -p build/$(DIST_DIR)/ovirtlib
	cp Makefile ovirtlib_setup.py ovirtlib/README.md $(SPEC) build/$(DIST_DIR)
	cp ovirtlib/*.py{,.in} build/$(DIST_DIR)/ovirtlib
	tar zcf $(TARBALL) -C build $(DIST_DIR)

.PHONY: rpm
rpm: dist
	rpmbuild --ta $(TARBALL)

.PHONY: all
all: $(GENERATED)
	$(PYTHON) ovirtlib_setup.py build

install:
	$(PYTHON) ovirtlib_setup.py install -O1 --root=$(DESTDIR) --record=INSTALLED_FILES.$(PYTHON)
