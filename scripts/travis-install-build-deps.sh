#!/bin/sh -e
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    build-essential \
    devscripts \
    equivs \
    gir1.2-gtk-3.0 \
    python3-flake8 \
    python3-gi \
    python3-setuptools \
    python3-yaml
mk-build-deps -i -r -s sudo \
	-t 'apt-get --yes --no-install-recommends --no-install-suggests'
