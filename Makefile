# BEWARE: this makefile is solely used for preparing a release - it is not useful for compiling/installing the program

# use something like "VERSION=0.2 make" to override the VERSION on the command line
VERSION ?= $(shell sed -n "s/^.*[\t ]*version[\t ]*=[\t ]*[\"']\([^\"']*\)[\"'].*/\1/gp" setup.py)
SVN_BASE ?= https://pycam.svn.sourceforge.net/svnroot/pycam
RELEASE_PREFIX ?= pycam-
ARCHIVE_DIR_RELATIVE ?= release-archives
EXPORT_DIR = $(RELEASE_PREFIX)$(VERSION)
EXPORT_FILE_PREFIX = $(EXPORT_DIR)
EXPORT_ZIP = $(EXPORT_FILE_PREFIX).zip
EXPORT_TGZ = $(EXPORT_FILE_PREFIX).tar.gz
EXPORT_WIN32 = $(EXPORT_FILE_PREFIX).win32.exe

# turn the destination directory into an absolute path
ARCHIVE_DIR := $(shell pwd)/$(ARCHIVE_DIR_RELATIVE)

.PHONY: zip tgz win32 clean dist svn_export upload create_archive_dir

dist: zip tgz win32
	@# remove the tmp directory when everything is done
	@rm -rf "$(EXPORT_DIR)"

clean:
	@rm -rf "$(EXPORT_DIR)"

svn_export: clean
	svn export --quiet "$(SVN_BASE)/trunk" "$(EXPORT_DIR)"

create_archive_dir:
	mkdir -p "$(ARCHIVE_DIR)"

zip: create_archive_dir svn_export
	cd "$(EXPORT_DIR)"; python setup.py sdist --format zip --dist-dir "$(ARCHIVE_DIR)"

tgz: create_archive_dir svn_export
	cd "$(EXPORT_DIR)"; python setup.py sdist --format gztar --dist-dir "$(ARCHIVE_DIR)"

win32: create_archive_dir svn_export
	# this is a binary release
	cd "$(EXPORT_DIR)"; python setup.py bdist --format wininst --dist-dir "$(ARCHIVE_DIR)"

upload:
	svn cp "$(SVN_BASE)/trunk" "$(SVN_BASE)/tags/release-$(VERSION)" -m "tag release $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_ZIP)" "$(SVN_BASE)/tags/archives/$(EXPORT_ZIP)" -m "added released zip file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_TGZ)" "$(SVN_BASE)/tags/archives/$(EXPORT_TGZ)" -m "added released tgz file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_WIN32)" "$(SVN_BASE)/tags/archives/$(EXPORT_WIN32)" -m "added released win32 installer for version $(VERSION)"

