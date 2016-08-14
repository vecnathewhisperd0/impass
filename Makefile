#!/usr/bin/make -f
# -*- makefile -*-

VERSION:=$(shell git describe --tags | sed -e s/_/~/ -e s/-/+/ -e s/-/~/ -e 's|.*/||')

.PHONY: all
all: assword.1

.PHONY: test
test:
	./test/assword-test $(TEST_OPTS)
	rm -f test/gnupg/S.gpg-agent

define ASSWORD_TMP
#!/bin/sh
PYTHONPATH=.. python3 -m assword "$$@"
endef
assword.1: assword assword.1.additional
	mkdir -p tmp
	$(file > assword.sh,$(ASSWORD_TMP))
	mv assword.sh tmp/assword
	chmod 755 tmp/assword
	help2man tmp/assword \
	-N -n 'Simple and secure password management system' \
	--version-string=$(VERSION) \
	--include=assword.1.additional \
	-o $@
	rm tmp/assword
	rmdir tmp

.PHONY: clean
clean:
	rm -f assword.1

.PHONY: debian-snapshot
debian-snapshot:
	rm -rf build/deb
	mkdir -p build/deb/debian
	git archive HEAD | tar -x -C build/deb/
	git archive debian:debian | tar -x -C build/deb/debian/
	cd build/deb; dch -b -v $(VERSION) -D UNRELEASED 'test build, not for upload'
	cd build/deb; echo '3.0 (native)' > debian/source/format
	cd build/deb; debuild -us -uc
