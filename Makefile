# use something like "VERSION=0.2 make" to override the VERSION on the command line
VERSION ?= svn
SVN_BASE = https://pycam.svn.sourceforge.net/svnroot/pycam
RELEASE_PREFIX = pycam-
EXPORT_DIR = $(RELEASE_PREFIX)$(VERSION)
EXPORT_FILE_PREFIX = $(EXPORT_DIR)


.PHONY: zip tgz svn_export tag

dist: zip tgz
	@# remove the tmp directory when everything is done
	@rm -rf "$(EXPORT_DIR)"

clean:
	@rm -rf "$(EXPORT_DIR)"

svn_export: clean
	svn export --quiet "$(SVN_BASE)/trunk" "$(EXPORT_DIR)"

zip: svn_export
	zip -9rq "$(EXPORT_FILE_PREFIX).zip" "$(EXPORT_DIR)"

tgz: svn_export
	tar czf "$(EXPORT_FILE_PREFIX).tar.gz" "$(EXPORT_DIR)"

tag:
	svn cp "$(SVN_BASE)/trunk" "$(SVN_BASE)/tags/release-$(VERSION)"

