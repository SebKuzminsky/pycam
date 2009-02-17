VER=0.1.7b

all:

.PHONY: dist

dist:
	(cd ..; tar zcf pycam/pycam.tgz pycam/*{Makefile,TXT} pycam/*.py pycam/tests/*.py pycam/pycam/*/*.py pycam/pycam/*.py pycam/Samples/*/*.stl)

dist-ver:
	(cd ..; tar zcf pycam-$(VER).tgz pycam-$(VER)/*{Makefile,TXT} pycam-$(VER)/*.py pycam-$(VER)/tests/*.py pycam-$(VER)/pycam/*/*.py pycam-$(VER)/pycam/*.py pycam-$(VER)/Samples/*/*.{stl,cfg})

