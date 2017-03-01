# -*- coding: utf-8 -*-
"""
Copyright 2008 Lode Leroy

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import subprocess


try:
    from Version import VERSION
except:
    # Failed to import Version.py, we must be running out of a git
    # checkout where the user forgot to run `make pycam/Version.py`.
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    git_proc = subprocess.Popen(["./scripts/get-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=repo_dir)
    stdout, stderr = git_proc.communicate()
    if git_proc.returncode == 0:
	VERSION = stdout.strip()
    else:
	# No pycam/Version.py and git failed to give us a version number, give up.
	VERSION = "0.0-unknown"


FILTER_CONFIG = (("Config files", "*.conf"),)
HELP_WIKI_URL = "http://sourceforge.net/apps/mediawiki/pycam/index.php?title=%s"
