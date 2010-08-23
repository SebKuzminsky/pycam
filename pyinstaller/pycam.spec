# -*- mode: python -*-
BASE_DIR = os.getcwd()
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), os.path.join(BASE_DIR, 'pycam')],
    pathex=[os.path.join(BASE_DIR, "src")],
    hookspath=[os.path.join(BASE_DIR, "pyinstaller", "hooks")])

pyz = PYZ(a.pure)

data = [("pycam-project.ui", os.path.join(BASE_DIR, "share", "gtk-interface", "pycam-project.ui"), "DATA"),
        ("menubar.xml", os.path.join(BASE_DIR, "share", "gtk-interface", "menubar.xml"), "DATA"),
        ("logo_gui.bmp", os.path.join(BASE_DIR, "share", "gtk-interface", "logo_gui.bmp"), "DATA"),
]

# import VERSION for the output filename
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from pycam import VERSION

samples = Tree(os.path.join(BASE_DIR, "samples"), prefix="samples")

exe = EXE(pyz, data, samples,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join(BASE_DIR, "pycam-%s_standalone.exe" % VERSION),
          debug=False,
          strip=False,
          upx=True,
          console=True )
