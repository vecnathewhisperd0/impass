#!/usr/bin/env python3

# much of the structure here was cribbed from
# https://github.com/pypa/sampleproject

from setuptools import setup

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

version = {}
with open("impass/version.py") as f:
    exec(f.read(), version)

setup(
    name="impass",
    version=version["__version__"],
    description="Simple and secure password management system.",
    long_description=long_description,
    author="Jameson Rollins",
    author_email="jrollins@finestructure.net",
    url="https://salsa.debian.org/debian/impass",
    license="GPLv3+",
    packages=["impass"],
    keywords=["passwords password-management"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        # maybe extend this?  "impass gui" won't work on anything but
        # X11, but the rest of it might still be useful.
        "Environment :: X11 Applications",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
    ],
    install_requires=[
        "gpg",
        "PyGobject",
    ],
    # You can install this optional dependency using the following syntax:
    # $ pip install -e .xdo
    extras_require={
        "xdo": ["xdo"],
    },
    # https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
    # should we have a 'gui_scripts' as well?
    entry_points={
        "console_scripts": [
            "impass = impass.__main__:main",
        ],
    },
)
