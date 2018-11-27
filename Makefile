#!/usr/bin/make -f
# -*- makefile -*-

VERSION:=$(shell git describe --tags | sed -e s/_/~/ -e s/-/+/ -e s/-/~/ -e 's|.*/||')

.PHONY: all
all: impass.1

.PHONY: test
test:
	./test/impass-test $(TEST_OPTS)
	rm -f test/gnupg/S.gpg-agent

impass.1: impass
	PYTHONPATH=. python3 -m impass help \
	| txt2man -t impass -r 'impass $(VERSION)' -s 1 \
	> impass.1

version:
	echo "__version__ = '$(VERSION)'" >impass/version.py

.PHONY: clean
clean:
	rm -f impass.1

.PHONY: debian-snapshot
debian-snapshot:
	rm -rf build/deb
	mkdir -p build/deb/debian
	git archive HEAD | tar -x -C build/deb/
	git archive --format=tar debian/master:debian | tar -x -C build/deb/debian/
	cd build/deb; dch -b -v $(VERSION) -D UNRELEASED 'test build, not for upload'
	cd build/deb; echo '3.0 (native)' > debian/source/format
	cd build/deb; debuild -us -uc
