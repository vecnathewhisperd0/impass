impass - simple and secure password management system
======================================================

impass is a secure password manager that relies on your OpenPGP key
for security and is designed to integrate in a minimal fashion into
any X11 window manager.  It also integrates into sway for a wayland
session.

Passwords and context strings are stored in a single OpenPGP-encrypted
and signed file (meaning entry contexts are not exposed to the
filesystem).  Along with a simple command-line interface, there is a
streamlined GUI meant for X11 window manager integration or sway when
using Wayland.

When invoked, the GUI produces a prompt to search stored contexts.
New entries can also easily be created.  Passwords are securely
retrieved without displaying on the screen.  Multiple retrieval
methods are available, including auto-typing them directly into an X11
window (default), or inserting them into the X11 clipboard.

impass was previously known as "assword".


Contact
=======

impass was written by:

    Jameson Graef Rollins <jrollins@finestructure.net>
    Daniel Kahn Gillmor <dkg@fifthhorseman.net>

impass has a mailing list:

    assword@lists.mayfirst.org
    https://lists.mayfirst.org/mailman/listinfo/assword

We also hang out on IRC:

    channel: #assword
    server:  irc.oftc.net


Getting impass
==============

Source
------

Clone the repo:

    $ git clone https://salsa.debian.org/debian/impass.git

Dependencies :
  * python3
  * python3-gpg - Python bindings for the GPGME library
  * python3-setuptools - Python packaging and distribution utilities

Recommends (for graphical UI):

  * python3-gi - Python bindings for GObject Introspection
  * gir1.2-gtk-3.0 - GObject Introspection for GTK 3+ (GUI toolkit)

Recommends (for curses UI):
  * python3-xdo - Support for simulating X11 input (libxdo bindings)
  * xclip - Support for accessing X11 clipboard

Recommends (for sway integration):
  * i3ipc - talk to sway
  * wtype - emulate keyboard input

Debian
------

impass is available in Debian: https://packages.qa.debian.org/impass

Debian/Ubuntu snapshot packages can also be easily made from the git
source.  You can build the package from any branch but it requires an
up-to-date local branch of origin/debian, e.g.:

    $ git branch debian/master origin/debian/master

Then:

    $ sudo apt install build-essential devscripts pkg-config python3-all-dev python3-setuptools debhelper dpkg-dev fakeroot txt2man
    $ make debian-snapshot
    $ sudo apt install build/impass_*.deb
 

Using impass
============

See the included impass(1) man page or built-in help string for
detailed usage.
