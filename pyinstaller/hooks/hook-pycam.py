# keysyms does not seem to be recognized by pyinstaller
# There will be exceptions after any keypress without this line.
# rsvg is required for SVG icons (dynamically loaded on demand)
hiddenimports = ["gtk.keysyms", "rsvg"]
