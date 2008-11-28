BRLCAD=/opt/brlcad/bin
BRLCAD=c:/Software/BRL-CAD/bin

MGED=$(BRLCAD)/mged
G-STL=$(BRLCAD)/g-stl
VER=0.1.6

all:

.PHONY: dist

dist:
	(cd ..; tar zcf pycam/pycam.tgz pycam/*{Makefile,TXT,txt} pycam/*.py pycam/tests/*.py pycam/pycam/*/*.py pycam/pycam/*.py pycam/Samples/*/*.stl)

dist-ver:
	(cd ..; tar zcf pycam-$(VER)/pycam-$(VER).tgz pycam-$(VER)/*{Makefile,TXT} pycam-$(VER)/*.py pycam-$(VER)/tests/*.py pycam-$(VER)/pycam/*/*.py pycam-$(VER)/pycam/*.py pycam-$(VER)/Samples/*/*.stl)

test:
	rm -f test.g; $(MGED) test.g < test.txt; $(MGED) test.g

test0:
	rm -f test.g; $(MGED) test.g < cutter0.txt; $(MGED) test.g

test1:
	rm -f test.g; $(MGED) test.g < cutter1.txt; $(MGED) test.g

test2:
	rm -f test.g; $(MGED) test.g < cutter2.txt; $(MGED) test.g

test3:
	rm -f test.g; $(MGED) test.g < cutter3.txt; $(MGED) test.g


TestModel.stl:
	./Tests/MGEDExporterTest.py
	rm -f TestModel.g
	$(MGED) TestModel.g < TestModel.txt
	$(G-STL) -o TestModel.stl TestModel.g model0
