# -*- mode: python -*-
BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(locals()["spec"]),
        os.path.pardir))
UI_DATA_RELATIVE = os.path.join("share", "ui")
UI_DATA_DIR = os.path.join(BASE_DIR, UI_DATA_RELATIVE)

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
            if "libpango-1.0-0.dll" in files:
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

more_libs.append(("msjava.dll", "msjava.dll", "BINARY"))

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

# First we have to know where gtk is installed, we get this from registry
import _winreg
import msvcrt
try:
    k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'Software\\GTK2-Runtime')
except EnvironmentError:
    print 'You must install the Gtk+ 2.2 Runtime Environment to run this program'
    while not msvcrt.kbhit():
        pass
    sys.exit(1)
else:    
    gtkdir = str(_winreg.QueryValueEx(k, 'InstallationDirectory')[0])
    gtkversion = str(_winreg.QueryValueEx(k, 'BinVersion')[0])
    # TODO: fix this hard-coded path
    engines_dir = os.path.normpath("C:/Python26/Lib/site-packages/gtk-2.0/runtime/lib/gtk-2.0/2.10.0/engines")
    if not os.path.isdir(engines_dir):
        print "Failed to locate the engines directory: %s" % str(engines_dir)
        sys.exit(1)

#Then we want to go to the directory where the gtkrcfile is located
gtkrc_dir = os.path.join('share', 'themes', 'MS-Windows', 'gtk-2.0')
if not os.path.isdir(gtkrc_dir):
    gtkrc_dir = os.path.normpath("C:/Python26/Lib/site-packages/gtk-2.0/runtime/share/themes/MS-Windows/gtk-2.0")

#Add gtkrc file to exe
data.append(('gtkrc', os.path.join(gtkdir, gtkrc_dir, 'gtkrc'), 'DATA'))

#Add libwimp.dll to exe (needed for the MS-Windows theme)
more_libs.append(('libwimp.dll', os.path.join(gtkdir, engines_dir, 'libwimp.dll'), 'BINARY'))

themes = Tree(os.path.join(gtkrc_dir, os.pardir, os.pardir, os.pardir, "icons"),
        prefix=os.path.join("share", "icons"))

icon_file = os.path.join(BASE_DIR, "share", "pycam.ico")

a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), os.path.join(BASE_DIR, 'pycam'), os.path.join(BASE_DIR, "src", "use_gtk.py")],
    pathex=[os.path.join(BASE_DIR, "src")],
    hookspath=[os.path.join(BASE_DIR, "pyinstaller", "hooks")])

pyz = PYZ(a.pure)

exe = EXE(pyz, data, samples, gtk_pixbuf_loaders, themes, fonts,
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

