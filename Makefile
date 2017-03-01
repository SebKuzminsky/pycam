# export SVN_REPO_BASE=. if you want to use the local version instead of trunk
# from the subversion repository.

VERSION ?= $(shell git describe --tags | sed 's/^v//')
REPO_TAGS ?= https://pycam.svn.sourceforge.net/svnroot/pycam/tags
RELEASE_PREFIX ?= pycam-
ARCHIVE_DIR_RELATIVE ?= release-archives
EXPORT_DIR = build/$(RELEASE_PREFIX)$(VERSION)
EXPORT_FILE_PREFIX = $(EXPORT_DIR)
EXPORT_ZIP = $(EXPORT_FILE_PREFIX).zip
EXPORT_TGZ = $(EXPORT_FILE_PREFIX).tar.gz
EXPORT_WIN32 = $(EXPORT_FILE_PREFIX).win32.exe
PYTHON_EXE ?= python
# check if the local version of python's distutils support "--plat-name"
# (introduced in python 2.6)
DISTUTILS_PLAT_NAME = $(shell $(PYTHON_EXE) setup.py --help build_ext \
		      | grep -q -- "--plat-name" && echo "--plat-name win32")
PYTHON_CHECK_STYLE_TARGETS = pycam Tests pyinstaller/hooks/hook-pycam.py scripts/pycam setup.py

# default location of mkdocs' build process
MKDOCS_SOURCE_DIR = docs
MKDOCS_EXPORT_DIR = site
MKDOCS_SOURCE_FILES = $(shell find "$(MKDOCS_SOURCE_DIR)" -type f)
MKDOCS_BUILD_STAMP = $(MKDOCS_EXPORT_DIR)/.build-stamp
# specify the remote user (e.g. for sourceforge: user,project) via ssh_config or directly on the
# commandline: "make upload-docs SF_USER=foobar"
ifdef SF_USER
WEBSITE_UPLOAD_PREFIX ?= $(SF_USER),pycam@
endif
WEBSITE_UPLOAD_LOCATION ?= web.sourceforge.net:/home/project-web/pycam/htdocs

# turn the destination directory into an absolute path
ARCHIVE_DIR := $(shell pwd)/$(ARCHIVE_DIR_RELATIVE)
RM = rm -f

.PHONY: zip tgz win32 clean dist git_export upload create_archive_dir man check-style test \
	pylint-relaxed pylint-strict docs upload-docs deb

dist: zip tgz win32
	@# remove the tmp directory when everything is done
	@$(RM) -r "$(EXPORT_DIR)"

clean:
	@$(RM) -r "$(EXPORT_DIR)"
	@$(RM) -r "$(MKDOCS_EXPORT_DIR)"
	$(MAKE) -C man clean

man:
	@$(MAKE) -C man man

git_export: clean
	@if git status 2>/dev/null >&2;\
		then git clone . "$(EXPORT_DIR)";\
		else echo "No git repo found."; exit 1;\
	fi
	# Windows needs a different name for the startup script - due to process creation
	# (no fork/exec)
	@cp "$(EXPORT_DIR)/scripts/pycam" "$(EXPORT_DIR)/scripts/pycam-loader.py"
	# overwrite dynamic version detection with a hardcoded string and update deb changelog
	cd "$(EXPORT_DIR)"; \
		echo 'VERSION = "$(VERSION)"' >pycam/version.py; \
		debchange --newversion "$$(echo "$(VERSION)" | tr - .)" "Upstream build"; \
		debchange --release ""

create_archive_dir:
	@mkdir -p "$(ARCHIVE_DIR)"

zip: create_archive_dir man git_export
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py sdist --format zip --dist-dir "$(ARCHIVE_DIR)"

tgz: create_archive_dir man git_export
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py sdist --format gztar --dist-dir "$(ARCHIVE_DIR)"

win32: create_archive_dir man git_export
	# this is a binary release
	cd "$(EXPORT_DIR)"; $(PYTHON_EXE) setup.py bdist_wininst --user-access-control force \
		--dist-dir "$(ARCHIVE_DIR)" $(DISTUTILS_PLAT_NAME)

deb: git_export
	cd "$(EXPORT_DIR)"; dpkg-buildpackage -us -uc

upload:
	svn cp "$(SVN_REPO_BASE)" "$(REPO_TAGS)/release-$(VERSION)" -m "tag release $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_ZIP)" "$(REPO_TAGS)/archives/$(EXPORT_ZIP)" \
		-m "added released zip file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_TGZ)" "$(REPO_TAGS)/archives/$(EXPORT_TGZ)" \
		-m "added released tgz file for version $(VERSION)"
	svn import "$(ARCHIVE_DIR)/$(EXPORT_WIN32)" "$(REPO_TAGS)/archives/$(EXPORT_WIN32)" \
		-m "added released win32 installer for version $(VERSION)"

test: check-style

check-style:
	scripts/run_flake8 $(PYTHON_CHECK_STYLE_TARGETS)

pylint-strict:
	pylint $(PYTHON_CHECK_STYLE_TARGETS)

pylint-relaxed:
	pylint -d missing-docstring,invalid-name,pointless-string-statement,fixme,no-self-use \
		-d global-statement,unnecessary-pass,too-many-arguments,too-many-branches \
		-d too-many-instance-attributes,too-many-return-statements \
		-d too-few-public-methods,too-many-locals,using-constant-test \
		-d attribute-defined-outside-init,superfluous-parens,too-many-nested-blocks \
		-d too-many-statements,unused-argument,too-many-lines \
		-d too-many-boolean-expressions,too-many-public-methods \
		$(PYTHON_CHECK_STYLE_TARGETS)


## Building the documentation/website
docs: man $(MKDOCS_BUILD_STAMP)
	@$(MAKE) -C man html
	install -d "$(MKDOCS_EXPORT_DIR)/manpages/"
	install --target-directory="$(MKDOCS_EXPORT_DIR)/manpages/" man/*.html

$(MKDOCS_BUILD_STAMP): $(MKDOCS_SOURCE_FILES)
	mkdocs build
	touch "$@"
	
upload-docs: docs
	rsync -axz --delete --exclude=.DS_Store --exclude="$(notdir $(MKDOCS_BUILD_STAMP))" -e ssh \
		"$(MKDOCS_EXPORT_DIR)/" "$(WEBSITE_UPLOAD_PREFIX)$(WEBSITE_UPLOAD_LOCATION)/"
