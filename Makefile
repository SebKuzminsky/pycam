VER=0.1.8

all:

.PHONY: dist

dist:
	(cd ..; tar zcf pycam/pycam.tgz pycam/*{Makefile,TXT} pycam/*.py pycam/Tests/*.py pycam/pycam/*/*.py pycam/pycam/*.py pycam/Samples/*/*.stl)

dist-ver:
	(cd ..; tar zcf pycam-$(VER).tgz pycam-$(VER)/*{Makefile,TXT} pycam-$(VER)/*.py pycam-$(VER)/Tests/*.py pycam-$(VER)/pycam/*/*.py pycam-$(VER)/pycam/*.py pycam-$(VER)/Samples/*/*.{stl,cfg})

