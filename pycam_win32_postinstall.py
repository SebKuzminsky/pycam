import distutils.sysconfig
import os
import sys

try:
    logfile = os.path.join(distutils.sysconfig.PREFIX, "pycam-wininst-postinstall.log", "a")
except OSError:
    logfile = None
if logfile:
    sys.stdout = logfile
    sys.stderr = logfile

LINK_EXTENSION = ".lnk"

try:
    START_MENU_BASEDIR = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
except OSError:
    START_MENU_BASEDIR = get_special_folder_path("CSIDL_PROGRAMS")
except NameError:
    START_MENU_BASEDIR = "HELO"
START_MENU_SUBDIR = os.path.join(START_MENU_BASEDIR, "PyCAM")

# create a start menu item for pycam
PYTHON_EXE = os.path.join(distutils.sysconfig.EXEC_PREFIX, "python.exe")
START_SCRIPT = os.path.join(distutils.sysconfig.EXEC_PREFIX, "Scripts", "pycam_start.py")
RUN_TARGET = '%s "%s"' % (PYTHON_EXE, START_SCRIPT)

PYTHON_DATA_DIR = os.path.join(distutils.sysconfig.PREFIX, "share", "python-pycam")

# add some more doc files
DOC_FILES = [
        ("HOWTO.TXT", "Introduction"),
        ("LICENSE.TXT", "License"),
        ("README.TXT", "Readme")]
WEB_LINKS = [
        (r"http://sourceforge.net/projects/pycam/", "Project's Website"),
        (r"http://sourceforge.net/tracker/?group_id=237831&atid=1104176", "Report a Bug"),
        (r"http://sourceforge.net/projects/pycam/forums", "Forum Discussions"),
        (r"http://sourceforge.net/apps/mediawiki/pycam/", "Wiki")]

MENU_ITEMS = map(lambda v: (os.path.join(PYTHON_DATA_DIR, v[0]), v[1]), DOC_FILES)
MENU_ITEMS.extend(WEB_LINKS)

action = sys.argv[1]

if action == "-install":
    if not os.path.exists(START_MENU_SUBDIR):
        os.mkdir(START_MENU_SUBDIR)
    directory_created(START_MENU_SUBDIR)
    for menu_item in MENU_ITEMS:
        target, description = menu_item
        filename = os.path.join(START_MENU_SUBDIR, description) + LINK_EXTENSION
        create_shortcut(target, description, filename)
        file_created(filename)
    filename = os.path.join(START_MENU_SUBDIR, "Run PyCAM") + LINK_EXTENSION
    create_shortcut(PYTHON_EXE, "Run PyCAM", filename, START_SCRIPT)
    file_created(filename)
elif action == "-remove":
    pass
else:
    pass

