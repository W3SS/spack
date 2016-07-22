##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the LICENSE file for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
import base64
import os
import hashlib
from contextlib import contextmanager

import llnl.util.tty as tty
from llnl.util.filesystem import join_path

import spack
import spack.stage
import spack.error

from spack.util.executable import which

# Patch tool for patching archives.
_patch = which("patch", required=True)


class Patch(object):
    """This class describes a patch to be applied to some expanded
       source code."""

    def __init__(self, pkg, path_or_url, level):
        self.pkg_name = pkg.name
        self.path_or_url = path_or_url
        self.path = None
        self.url = None
        self.level = level
        self._file_hash = None

        if not isinstance(self.level, int) or not self.level >= 0:
            raise ValueError("Patch level needs to be a non-negative integer.")

        if '://' in path_or_url:
            self.url = path_or_url
        else:
            pkg_dir = spack.repo.dirname_for_package_name(self.pkg_name)
            self.path = join_path(pkg_dir, path_or_url)
            if not os.path.isfile(self.path):
                raise NoSuchPatchFileError(pkg_name, self.path)


    @property
    def file_hash(self):
        if not self._file_hash:
            with self.get_patch() as patch_file:
                self._file_hash = file_hash(patch_file)
                    
        return self._file_hash


    def apply(self, stage):
        """Fetch this patch, if necessary, and apply it to the source
           code in the supplied stage.
        """
        stage.chdir_to_source()

        patch_stage = None
        with self.get_patch() as patch_file:
            self._file_hash = file_hash(patch_file)

            # Use -N to allow the same patches to be applied multiple times.
            _patch('-s', '-p', str(self.level), '-i', patch_file)

    def get_patch(self):
        if self.url:
            return get_url(self.url)
        else:
            return get_file(self.path)


@contextmanager
def get_url(url):
    with spack.stage.Stage(self.url) as tmp_stage:
        tmp_stage.fetch()
        yield tmp_stage.archive_file


@contextmanager
def get_file(path):
    yield path
  

def file_hash(path):
    with open(path, 'rb') as F:
        return base64.b32encode(hashlib.md5(F.read()).digest()).lower()


class NoSuchPatchFileError(spack.error.SpackError):
    """Raised when user specifies a patch file that doesn't exist."""
    def __init__(self, package, path):
        super(NoSuchPatchFileError, self).__init__(
            "No such patch file for package %s: %s" % (package, path))
        self.package = package
        self.path = path
