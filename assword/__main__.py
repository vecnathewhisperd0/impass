#!/usr/bin/env python3

import os
import sys
import json
import gpgme
import getpass
import subprocess

import assword

############################################################

PROG = 'assword'

def version():
    print(assword.__version__)

def usage():
    print("Usage:", PROG, "<command> [<args>...]")
    print("""
The password database is stored as a single json object, OpenPGP
encrypted and signed, and written to local disk (see ASSWORD_DB).  The
file will be created upon addition of the first entry.  Database
entries are keyed by 'context'.  During retrieval of passwords, the
database is decrypted and read into memory.  Contexts are search by
sub-string match.

Commands:

  add [<context>]    Add a new entry.  If context is '-' read from stdin.
                     If not specified, user will be prompted for
                     context.  If the context already exists, an error
                     will be thrown.  See ASSWORD_PASSWORD for
                     information on passwords.

  replace [<context>]
                     Replace password for existing entry.  If context
                     is '-' read from stdin.  If not specified, user
                     will be prompted for context.  If the context
                     does not exist an error will be thrown. See
                     ASSWORD_PASSWORD for information on passwords.

  dump [<string>]    Dump search results as json.  If string not specified all
                     entries are returned.  Passwords will not be displayed
                     unless ASSWORD_DUMP_PASSWORDS is set.

  gui [<string>]     GUI interface, good for X11 window manager integration.
                     Upon invocation the user will be prompted to decrypt the
                     database, after which a graphical search prompt will be
                     presented.  If an additional string is provided, it will
                     be added as the initial search string.  All matching results
                     for the query will be presented to the user.  When a result
                     is selected, the password will be retrieved according to the
                     method specified by ASSWORD_XPASTE.  If no match is found,
                     the user has the opportunity to generate and store a new
                     password, which is then delivered via ASSWORD_XPASTE.

  remove <context>   Delete an entry from the database.

  version            Report the version of this program.

  help               This help.

Environment:

  ASSWORD_DB        Path to assword database file.  Default: ~/.assword/db

  ASSWORD_KEYFILE   File containing OpenPGP key ID of database encryption
                    recipient.  Default: ~/.assword/keyid

  ASSWORD_KEYID     OpenPGP key ID of database encryption recipient.  This
                    overrides ASSWORD_KEYFILE if set.

  ASSWORD_PASSWORD  For new entries, entropy of auto-generated password
                    in bytes (actual generated password will be longer
                    due to base64 encoding). If set to 'prompt' user
                    will be prompted for for password.  Default: %d

  ASSWORD_DUMP_PASSWORDS Include passwords in dump when set.

  ASSWORD_XPASTE    Method for password retrieval.  Options are: 'xdo', which
                    attempts to type the password into the window that had
                    focus on launch, or 'xclip' which inserts the password in
                    the X clipboard.  Default: xdo
"""%(assword.DEFAULT_NEW_PASSWORD_OCTETS))

############################################################

ASSWORD_DIR = os.path.join(os.path.expanduser('~'),'.assword')

DBPATH = os.getenv('ASSWORD_DB', os.path.join(ASSWORD_DIR, 'db'))

############################################################

def xclip(text):
    p = subprocess.Popen(' '.join(["xclip", "-i"]),
                         shell=True,
                         stdin=subprocess.PIPE)
    p.communicate(text.encode('utf-8'))

############################################################
# Return codes:
# 1 command/load line error
# 2 context/password invalid
# 5 db doesn't exist
# 10 db error
# 20 gpg/key error
############################################################
def error(code, msg=''):
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)

def open_db(keyid=None, create=False):
    if not create and not os.path.exists(DBPATH):
        error(5, """Assword database does not exist.
To add an entry to the database use 'assword add'.
See 'assword help' for more information.""")
    try:
        db = assword.Database(DBPATH, keyid)
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    if db.sigvalid is False:
        print("WARNING: could not validate OpenPGP signature on db file.", file=sys.stderr)
    return db

def get_keyid():
    keyid = os.getenv('ASSWORD_KEYID')
    keyfile = os.getenv('ASSWORD_KEYFILE', os.path.join(ASSWORD_DIR, 'keyid'))

    if not keyid and os.path.exists(keyfile):
        with open(keyfile, 'r') as f:
            keyid = f.read().strip()

    save = False
    if not keyid:
        print("OpenPGP key ID of encryption target not specified.", file=sys.stderr)
        print("Please provide key ID in ASSWORD_KEYID environment variable,", file=sys.stderr)
        print("or specify key ID now to save in ~/.assword/keyid file.", file=sys.stderr)
        keyid = input('OpenPGP key ID: ')
        if keyid == '':
            keyid = None
        else:
            save = True

    if not keyid:
        error(20)

    try:
        gpg = gpgme.Context()
        gpg.get_key(keyid)
    except gpgme.GpgmeError as e:
        print("GPGME error for key ID %s:" % keyid, file=sys.stderr)
        print("  %s" % e, file=sys.stderr)
        error(20)

    if save:
        if not os.path.isdir(os.path.dirname(keyfile)):
            os.mkdir(os.path.dirname(keyfile))
        with open(keyfile, 'w') as f:
            f.write(keyid)

    return keyid

def retrieve_context(args):
    try:
        # get context as argument
        context = args[0]
        # or from stdin
        if context == '-':
            context = sys.stdin.read()
    # prompt for context if not specified
    except IndexError:
        try:
            context = input('context: ')
        except KeyboardInterrupt:
            sys.exit(-1)
    if context == '':
        sys.exit("Can not add empty string context.")
    return context

def retrieve_password():
    # get password from prompt if requested
    if os.getenv('ASSWORD_PASSWORD') is None:
        return None
    elif os.getenv('ASSWORD_PASSWORD') != 'prompt':
        try:
            octets = int(os.getenv('ASSWORD_PASSWORD'))
        except ValueError:
            sys.exit("ASSWORD_PASSWORD environment variable is neither int or 'prompt'.")
        print("Auto-generating password...", file=sys.stderr)
        return octets
    try:
        password0 = getpass.getpass('password: ')
        password1 = getpass.getpass('reenter password: ')
        if password0 != password1:
            error(2, "Passwords do not match.  Aborting.")
        return password0
    except KeyboardInterrupt:
        error(-1)

############################################################
# command functions

# Add a password to the database.
# First argument is potentially a context.
def add(args):
    keyid = get_keyid()
    context = retrieve_context(args)
    db = open_db(keyid, create=True)
    if context in db:
        error(2, "Context '%s' already exists.")

    password = retrieve_password()
    try:
        db.add(context.strip(), password)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("New entry writen.", file=sys.stderr)

# Replace a password in the database.
# First argument is context to replace.
def replace(args):
    keyid = get_keyid()
    context = retrieve_context(args)
    db = open_db(keyid)
    if context not in db:
        error(2, "Context '%s' not found." % (context))

    password = retrieve_password()
    try:
        db.replace(context.strip(), password)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("Password replaced.", file=sys.stderr)

def dump(args):
    query = ' '.join(args)
    db = open_db()
    results = db.search(query)
    output = {}
    for context in results:
        output[context] = {}
        output[context]['date'] = results[context]['date']
        if os.getenv('ASSWORD_DUMP_PASSWORDS'):
            output[context]['password'] = results[context]['password']
    print(json.dumps(output, sort_keys=True, indent=2))

# The X GUI
def gui(args, method='xdo'):
    from assword.gui import Gui
    if method == 'xdo':
        try:
            import xdo
        except:
            error(1, """The xdo module is not found, so the 'xdo' paste method is not available.
Please install python3-xdo.""")
        # initialize xdo
        x = xdo.xdo()
        # get the id of the currently focused window
        win = x.get_focused_window()
    elif method == 'xclip':
        pass
    else:
        error(1, "Unknown X paste method '%s'." % method)
    query = ' '.join(args)
    keyid = get_keyid()
    db = open_db(keyid)
    result = Gui(db, query=query).returnValue()
    # type the password in the saved window
    if result:
        if method == 'xdo':
            x.focus_window(win)
            x.wait_for_window_focus(win)
            x.type(result['password'])
        elif method == 'xclip':
            xclip(result['password'])

def remove(args):
    keyid = get_keyid()
    try:
        context = args[0]
    except IndexError:
        print("Must specify index to remove.", file=sys.stderr)
        sys.exit(1)
    db = open_db(keyid)
    if context not in db:
        error(2, "Context '%s' not found." % (context))

    try:
        print("Really remove entry '%s'?" % (context), file=sys.stderr)
        response = input("Type 'yes' to remove: ")
    except KeyboardInterrupt:
        error(-1)
    if response != 'yes':
        error(-1)

    try:
        db.remove(context)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("Entry removed.", file=sys.stderr)

############################################################
# main

def main():
    if len(sys.argv) < 2:
        print("Command not specified.", file=sys.stderr)
        print(file=sys.stderr)
        usage()
        error(1)

    cmd = sys.argv[1]

    if cmd == 'add':
        add(sys.argv[2:])
    elif cmd == 'replace':
        replace(sys.argv[2:])
    elif cmd == 'dump':
        dump(sys.argv[2:])
    elif cmd == 'gui':
        method = os.getenv('ASSWORD_XPASTE', 'xdo')
        gui(sys.argv[2:], method=method)
    elif cmd == 'remove':
        remove(sys.argv[2:])
    elif cmd == 'version' or cmd == '--version':
        version()
    elif cmd == 'help' or cmd == '--help':
        print
        usage()
    else:
        print("Unknown command:", cmd, file=sys.stderr)
        print(file=sys.stderr)
        usage()
        error(1)

if __name__ == "__main__":
    main()
