# export SVN_REPO_BASE=. if you want to use the local version instead of trunk
# from the subversion repository.

# use something like "VERSION=0.2 make" to override the VERSION on the command line
VERSION ?= $(shell sed -n "s/^.*[\t ]*VERSION[\t ]*=[\t ]*[\"']\([^\"']*\)[\"'].*/\1/gp" src/pycam/__init__.py)
SVN_REPO_BASE ?= $(shell svn info --xml 2>/dev/null | grep "^<url>" | cut -f 2 -d ">" | cut -f 1 -d "<")
SVK_REPO_BASE ?= $(shell LANG= svk info 2>/dev/null| grep "^Depot Path:" | cut -f 3- -d " ")
REPO_TAGS ?= https://pycam.svn.sourceforge.net/svnroot/pycam/tags
RELEASE_PREFIX ?= pycam-
ARCHIVE_DIR_RELATIVE ?= release-archives
EXPORT_DIR = $(RELEASE_PREFIX)$(VERSION)
EXPORT_FILE_PREFIX = $(EXPORT_DIR)
EXPORT_ZIP = $(EXPORT_FILE_PREFIX).zip
EXPORT_TGZ = $(EXPORT_FILE_PREFIX).tar.gz
EXPORT_WIN32 = $(EXPORT_FILE_PREFIX).win32.exe
PYTHON_EXE ?= python
# check if the local version of python's distutils support "--plat-name"
# (introduced in python 2.6)
DISTUTILS_PLAT_NAME = $(shell $(PYTHON_EXE) setup.py --help build_ext | grep -q -- "--plat-name" && echo "--plat-name win32")

# turn the destination directory into an absolute path
ARCHIVE_DIR := $(shell pwd)/$(ARCHIVE_DIR_RELATIVE)

.PHONY: zip tgz win32 clean dist svn_export upload create_archive_dir man

dist: zip tgz win32
	@# remove the tmp directory when everything is done
	@rm -rf "$(EXPORT_DIR)"

clean:
	@rm -rf "$(EXPORT_DIR)"

man: svn_export
	@make -C "$(EXPORT_DIR)/man"

svn_export: clean
	@if svn info 2>/dev/null >&2;\
		then svn export --quiet "$(SVN_REPO_BASE)" "$(EXPORT_DIR)";\
		else svk co "$(SVK_REPO_BASE)" "$(EXPORT_DIR)";\
	fi
	# Windows needs a different name for the startup script - due to process creation (no fork/exec)
	@cp "$(EXPORT_DIR)/pycam" "$(EXPORT_DIR)/pycam-loader.py"

create_archive_dir:
	@mkdir -p "$(ARCHIVE_DIR)"

zip: create_archive_dir man svn_export
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py sdist --format zip --dist-dir "$(ARCHIVE_DIR)"

tgz: create_archive_dir man svn_export
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py sdist --format gztar --dist-dir "$(ARCHIVE_DIR)"

win32: create_archive_dir man svn_export
	# this is a binary release
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py bdist_wininst --user-access-control force --dist-dir "$(ARCHIVE_DIR)" $(DISTUTILS_PLAT_NAME)

upload:
	svn cp "$(SVN_REPO_BASE)" "$(REPO_TAGS)/release-$(VERSION)" -m "tag release $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_ZIP)" "$(REPO_TAGS)/archives/$(EXPORT_ZIP)" -m "added released zip file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_TGZ)" "$(REPO_TAGS)/archives/$(EXPORT_TGZ)" -m "added released tgz file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_WIN32)" "$(REPO_TAGS)/archives/$(EXPORT_WIN32)" -m "added released win32 installer for version $(VERSION)"

