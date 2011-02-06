# -*- mode: python -*-
BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(locals()["spec"]),
        os.path.pardir))
UI_DATA_RELATIVE = os.path.join("share", "ui")
UI_DATA_DIR = os.path.join(BASE_DIR, UI_DATA_RELATIVE)
# We need to use a startup file ending with ".py" to allow forking in multiprocessing mode.
# Copy "pycam" to this file and remove it after building.
STARTUP_SCRIPT = os.path.join(BASE_DIR, "pycamGUI.py")
ORIGINAL_STARTUP_SCRIPT = os.path.join(BASE_DIR, "pycam")

data = [(os.path.join(UI_DATA_RELATIVE, "pycam-project.ui"), os.path.join(UI_DATA_DIR, "pycam-project.ui"), "DATA"),
        (os.path.join(UI_DATA_RELATIVE, "menubar.xml"), os.path.join(UI_DATA_DIR, "menubar.xml"), "DATA"),
        (os.path.join(UI_DATA_RELATIVE, "logo_gui.png"), os.path.join(UI_DATA_DIR, "logo_gui.png"), "DATA"),
]

# look for the location of "libpixbufloader-png.dll" (for Windows standalone executable)
start_dirs = (os.path.join(os.environ["PROGRAMFILES"], "Common files", "Gtk"),
        os.path.join(os.environ["COMMONPROGRAMFILES"], "Gtk"),
        "C:\\")
def find_gtk_pixbuf_dir(dirs):
    for start_dir in dirs:
        for root, dirs, files in os.walk(start_dir):
            if "libpixbufloader-png.dll" in files:
                return root
    return None
gtk_loaders_dir = find_gtk_pixbuf_dir(start_dirs)
if gtk_loaders_dir is None:
    print >>sys.stderr, "Failed to locate Gtk installation (looking for libpixbufloader-png.dll)"
    #sys.exit(1)
    gtk_loaders_dir = start_dirs[0]

# configure the pixbufloader (for the Windows standalone executable)
config_dir = gtk_loaders_dir
config_relative = os.path.join("etc", "gtk-2.0", "gdk-pixbuf.loaders")
while not os.path.isfile(os.path.join(config_dir, config_relative)):
    new_config_dir = os.path.dirname(config_dir)
    if (not new_config_dir) or (new_config_dir == config_dir):
        print >>sys.stderr, "Failed to locate '%s' around '%s'" \
                % (config_relative, gtk_loaders_dir)
        config_dir = None
        break
    config_dir = new_config_dir

if config_dir:
    gtk_pixbuf_config_file = os.path.join(config_dir, config_relative)
    data.append((config_relative, os.path.join(config_dir, config_relative), "DATA"))

# somehow we need to add glut32.dll manually
more_libs = []

def find_glut32(start_dir, filename="glut32.dll"):
    for root, dirs, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None
glut32_dll = find_glut32(sys.prefix)
if glut32_dll:
    more_libs.append((os.path.basename(glut32_dll), glut32_dll, "BINARY"))

def get_pixbuf_loaders_prefix(gtk_loaders_dir):
    prefix = []
    path_splits = gtk_loaders_dir.split(os.path.sep)
    while path_splits and (not prefix or (prefix[-1].lower() != "lib")):
        prefix.append(path_splits.pop())
    if prefix[-1].lower() == "lib":
        prefix.reverse()
        #return "\\".join(prefix)
        return os.path.join(*prefix)
    else:
        return None

gtk_pixbuf_loaders_prefix = get_pixbuf_loaders_prefix(gtk_loaders_dir)
if gtk_pixbuf_loaders_prefix is None:
    print >>sys.stderr, "Failed to extract the prefix from '%s'" % gtk_loaders_dir
    gtk_pixbuf_loaders = []
else:
    gtk_pixbuf_loaders = Tree(gtk_loaders_dir, prefix=gtk_pixbuf_loaders_prefix)

# import VERSION for the output filename
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from pycam import VERSION

samples = Tree(os.path.join(BASE_DIR, "samples"), prefix="samples")
fonts = Tree(os.path.join(BASE_DIR, "share", "fonts"), prefix=os.path.join("share", "fonts"))

icon_file = os.path.join(BASE_DIR, "share", "pycam.ico")

if os.path.exists(STARTUP_SCRIPT):
    print "New startup script already exists: %s" % STARTUP_SCRIPT
else:
    os.rename(ORIGINAL_STARTUP_SCRIPT, STARTUP_SCRIPT)

a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), STARTUP_SCRIPT],
    pathex=[os.path.join(BASE_DIR, "src")],
    hookspath=[os.path.join(BASE_DIR, "pyinstaller", "hooks")])

pyz = PYZ(a.pure)

# remove all ".svn" files
for file_list in (data, samples, gtk_pixbuf_loaders, fonts, a.datas):
    flist_copy = list(file_list)
    # clear the original list
    while file_list:
        file_list.pop()
    # add all items that don't contain a ".svn" directory name
    for fentry in flist_copy:
        if not ".svn" in fentry[0].split(os.path.sep):
            file_list.append(fentry)

exe = EXE(pyz, data, samples, gtk_pixbuf_loaders, fonts,
          a.scripts,
          a.binaries + more_libs,
          a.zipfiles,
          a.datas,
          name=os.path.join(BASE_DIR, "pycam-%s_standalone.exe" % VERSION),
          icon=icon_file,
          debug=False,
          strip=False,
          upx=True,
          console=True,
      )

if not os.path.exists(ORIGINAL_STARTUP_SCRIPT):
    os.rename(STARTUP_SCRIPT, ORIGINAL_STARTUP_SCRIPT)
else:
    print "Keeping original startup script: %s" % ORIGINAL_STARTUP_SCRIPT

