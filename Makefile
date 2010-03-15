# use something like "VERSION=0.2 make" to override the VERSION on the command line
VERSION ?= svn
SVN_BASE = https://pycam.svn.sourceforge.net/svnroot/pycam
RELEASE_PREFIX = pycam-
EXPORT_DIR = $(RELEASE_PREFIX)$(VERSION)
EXPORT_FILE_PREFIX = $(EXPORT_DIR)
EXPORT_ZIP = $(EXPORT_FILE_PREFIX).zip
EXPORT_TGZ = $(EXPORT_FILE_PREFIX).tar.gz
EXPORT_WIN32 = $(EXPORT_FILE_PREFIX).win32.exe
EXPORT_ARCHIVE_DIR = $(EXPORT_DIR)/dist


.PHONY: zip tgz win32 clean dist svn_export tag

dist: zip tgz win32
	@# remove the tmp directory when everything is done
	@rm -rf "$(EXPORT_DIR)"

clean:
	@rm -rf "$(EXPORT_DIR)"

svn_export: clean
	svn export --quiet "$(SVN_BASE)/trunk" "$(EXPORT_DIR)"

zip: svn_export
	python "$(EXPORT_DIR)/setup.py" sdist --format zip

tgz: svn_export
	python "$(EXPORT_DIR)/setup.py" sdist --format gztar

win32: svn_export
	# this is a binary release
	python "$(EXPORT_DIR)/setup.py" bdist --format wininst

tag:
	svn cp "$(SVN_BASE)/trunk" "$(SVN_BASE)/tags/release-$(VERSION)" -m "tag release $(VERSION)"
	svn import "$(EXPORT_ZIP)" "$(SVN_BASE)/tags/archives/$(EXPORT_ZIP)" -m "added released zip file for version $(VERSION)"
	svn import "$(EXPORT_TGZ)" "$(SVN_BASE)/tags/archives/$(EXPORT_TGZ)" -m "added released tgz file for version $(VERSION)"
	svn import "$(EXPORT_WIN32)" "$(SVN_BASE)/tags/archives/$(EXPORT_WIN32)" -m "added released win32 installer for version $(VERSION)"

