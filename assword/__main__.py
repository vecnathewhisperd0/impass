#!/usr/bin/env python3

import os
import sys
import json
import gpgme
import getpass
import argparse
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

  update [<old-context> [<new-context>]]
                     Update an existing context.  If the old context
                     does not exist an error will be thrown.

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

class Completer(object):
    def __init__(self, completions=None):
        self.completions = completions or []
    def completer(self, text, index):
        matching = [
            c for c in self.completions if c.startswith(text)
            ]
        try:
            return matching[index]
        except IndexError:
            return None

def input_complete(prompt, completions=None, default=None):
    try:
        # lifted from magic-wormhole/codes.py
        import readline
        c = Completer(completions)
        readline.set_startup_hook()
        if "libedit" in readline.__doc__:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        readline.set_completer(c.completer)
        readline.set_completer_delims(' ')
        if default:
            readline.set_startup_hook(lambda: readline.insert_text(default))
    except ImportError:
        pass
    try:
        return input(prompt)
    except KeyboardInterrupt:
        error(-1)

def retrieve_context(arg, prompt='context: ', default=None, stdin=True, db=None):
    if arg == '-' and stdin:
        context = sys.stdin.read()
    elif arg in [':', None]:
        if db:
            context = input_complete(prompt, completions=[c for c in db], default=default)
        else:
            context = input_complete(prompt, default=default)
    else:
        context = arg
    return context.strip()

class PasswordAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.getenv('ASSWORD_PASSWORD'):
            password = None
        elif os.getenv('ASSWORD_PASSWORD') in ['prompt',':']:
            password = ':'
        else:
            try:
                password = int(os.getenv('ASSWORD_PASSWORD'))
            except ValueError:
                error(1, "ASSWORD_PASSWORD environment variable is neither int nor 'prompt'.")
        # print('%s %s %s' % (parser, namespace, values))
        if values == ':':
            password = ':'
        elif values:
            try:
                password = int(values)
            except ValueError:
                error(666, "Don't type your password on the command line!!!")
        setattr(namespace, self.dest, password)

def retrieve_password(pwspec):
    if pwspec == ':':
        return input_password()
    else:
        print("Auto-generating password...", file=sys.stderr)
        return pwspec

def input_password():
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

def add(args):
    """Add a password to the database.

    If context is '-' read from stdin.  If context is ':' or not
    specified the user will be prompted.  If the context already
    exists an error will be thrown.  See ASSWORD_PASSWORD for
    information on passwords.

    """
    parser = argparse.ArgumentParser(prog=PROG+' add',
                                     description=add.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, or ':' for prompt, or '-' for stdin")
    parser.add_argument('pwspec', nargs='?', action=PasswordAction,
                        help="password spec: N octets or ':' for prompt")
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid, create=True)

    context = retrieve_context(args.context)
    if context in db:
        error(2, "Context '%s' already exists.")

    password = retrieve_password(args.pwspec)

    try:
        db.add(context, password)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("New entry writen.", file=sys.stderr)

def replace(args):
    """Replace a password in the database.

    If context is '-' read from stdin.  If context is ':' or not
    specified the user will be prompted.  If the context does not
    already exist an error will be thrown.  See ASSWORD_PASSWORD for
    information on passwords.

    """
    parser = argparse.ArgumentParser(prog=PROG+' replace',
                                     description=replace.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, or ':' for prompt, or '-' for stdin")
    parser.add_argument('pwspec', nargs='?', action=PasswordAction,
                        help="password spec: N octets or ':' for prompt")
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    context = retrieve_context(args.context, db=db)
    if context not in db:
        error(2, "Context '%s' not found." % (context))

    password = retrieve_password(args.pwspec)

    try:
        db.replace(context, password)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("Password replaced.", file=sys.stderr)

def update(args):
    """Update existing context in the database.

    Replace a context while keeping password the same.  If either
    context is not specified or ':' the user will be prompted for the
    respective context.

    """
    parser = argparse.ArgumentParser(prog=PROG+' update',
                                     description=update.__doc__)
    parser.add_argument('old_context', nargs='?',
                        help="existing database context, ':' for prompt, or '-' for stdin")
    parser.add_argument('new_context', nargs='?',
                        help="new database context or ':' for prompt")
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    old_context = retrieve_context(args.old_context, prompt='old context: ', db=db)
    if old_context not in db:
        error(2, "Context '%s' not found" % old_context)

    new_context = retrieve_context(args.new_context, prompt='new context: ', default=old_context, stdin=False)
    if new_context in db:
        error(2, "Context '%s' already exists." % new_context)

    try:
        db.update(old_context, new_context)
        db.save()
    except assword.DatabaseError as e:
        error(10, 'Assword database error: %s' % e.msg)
    print("Entry updated.", file=sys.stderr)

def dump(args):
    """Dump password database to stdout as json.

    If a string is provide only entries whose context contains the
    string will be dumped.  Otherwise all entries are returned.
    Passwords will not be displayed unless ASSWORD_DUMP_PASSWORDS is
    set.

    """
    parser = argparse.ArgumentParser(prog=PROG+' dump',
                                     description=remove.__doc__)
    parser.add_argument('string', nargs='?',
                        help="substring match for contexts")
    args = parser.parse_args(args)
    db = open_db()
    results = db.search(args.string)
    output = {}
    for context in results:
        output[context] = {}
        output[context]['date'] = results[context]['date']
        if os.getenv('ASSWORD_DUMP_PASSWORDS'):
            output[context]['password'] = results[context]['password']
    print(json.dumps(output, sort_keys=True, indent=2))

def gui(args, method='xdo'):
    """Launch minimal X GUI.

    Good for X11 window manager integration.  Upon invocation the user
    will be prompted to decrypt the database, after which a graphical
    search prompt will be presented.  If an additional string is
    provided, it will be added as the initial search string.  All
    matching results for the query will be presented to the user.
    When a result is selected, the password will be retrieved
    according to the method specified by ASSWORD_XPASTE.  If no match
    is found, the user has the opportunity to generate and store a new
    password, which is then delivered via ASSWORD_XPASTE.

    """
    parser = argparse.ArgumentParser(prog=PROG+' gui',
                                     description=remove.__doc__)
    parser.add_argument('string', nargs='?',
                        help="substring match for contexts")
    args = parser.parse_args(args)
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
    keyid = get_keyid()
    db = open_db(keyid)
    result = Gui(db, query=args.string).returnValue()
    # type the password in the saved window
    if result:
        if method == 'xdo':
            x.focus_window(win)
            x.wait_for_window_focus(win)
            x.type(result['password'])
        elif method == 'xclip':
            xclip(result['password'])

def remove(args):
    """Remove password from database.

    If context is '-' read from stdin.  If context is ':' or not
    specified the user will be prompted.  If the context does not
    already exist an error will be thrown.

    """
    parser = argparse.ArgumentParser(prog=PROG+' remove',
                                     description=remove.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, or ':' for prompt, or '-' for stdin")
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    context = retrieve_context(args.context, db=db)
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
    elif cmd == 'update':
        update(sys.argv[2:])
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
