#!/usr/bin/env python3

import os
import io
import sys
import json
import gpg
import getpass
import argparse
import textwrap
import subprocess
import collections

from .db import Database, DatabaseError, DEFAULT_NEW_PASSWORD_OCTETS
from .version import __version__

PROG = 'impass'

############################################################

IMPASS_DIR = os.path.join(os.path.expanduser('~'),'.impass')

############################################################

def xclip(text):
    p = subprocess.Popen(' '.join(["xclip", "-i"]),
                         shell=True,
                         stdin=subprocess.PIPE)
    p.communicate(text.encode('utf-8'))


def log(*args):
    print(*args, file=sys.stderr)


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
        log(msg)
    sys.exit(code)


def open_db(keyid=None, create=False):
    DBPATH = os.getenv('IMPASS_DB', os.path.join(IMPASS_DIR, 'db'))
    if not create and not os.path.exists(DBPATH):
        error(5, """Impass database does not exist.
To add an entry to the database use 'impass add'.
See 'impass help' for more information.""")
    try:
        db = Database(DBPATH, keyid)
    except gpg.errors.GPGMEError as e:
        error(20, "Decryption error: {}".format(e))
    except DatabaseError as e:
        error(10, "Impass database error: {}".format(e.msg))
    if db.sigvalid is False:
        log("WARNING: could not validate OpenPGP signature on db file.")
    return db


def get_keyid():
    keyid = os.getenv('IMPASS_KEYID')
    keyfile = os.getenv('IMPASS_KEYFILE', os.path.join(IMPASS_DIR, 'keyid'))

    if not keyid and os.path.exists(keyfile):
        with open(keyfile, 'r') as f:
            keyid = f.read().strip()

    save = False
    if not keyid:
        log("OpenPGP key ID of encryption target not specified.")
        log("Please provide key ID in IMPASS_KEYID environment variable,")
        log("or specify key ID now to save in ~/.impass/keyid file.")
        keyid = input('OpenPGP key ID: ')
        if keyid == '':
            keyid = None
        else:
            save = True

    if not keyid:
        error(20)

    try:
        gpgctx = gpg.Context()
        gpgctx.get_key(keyid, secret=False)
    except gpg.errors.GPGMEError as e:
        log("GPGME error for key ID {}:".format(keyid))
        log("  {}".format(e))
        error(20)

    if save:
        if not os.path.isdir(os.path.dirname(keyfile)):
            os.mkdir(os.path.dirname(keyfile))
        with open(keyfile, 'w') as f:
            f.write(keyid)

    return keyid


class Completer:
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
        if not os.getenv('IMPASS_PASSWORD'):
            password = None
        elif os.getenv('IMPASS_PASSWORD') in ['prompt',':']:
            password = ':'
        else:
            try:
                password = int(os.getenv('IMPASS_PASSWORD'))
            except ValueError:
                error(1, "IMPASS_PASSWORD environment variable is neither int nor 'prompt'.")
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
        log("Auto-generating password...")
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
    """Add new entry.

    If the context already exists in the database an error will be
    thrown.

    """
    parser = argparse.ArgumentParser(prog=PROG+' add',
                                     description=add.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, ':' for prompt, or '-' for stdin")
    parser.add_argument('pwspec', nargs='?', action=PasswordAction,
                        help="password spec: N octets or ':' for prompt")
    if args is None: return parser
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid, create=True)

    context = retrieve_context(args.context)
    if context in db:
        error(2, "Context '{}' already exists.".format(context))

    password = retrieve_password(args.pwspec)

    try:
        db.add(context, password)
        db.save()
    except DatabaseError as e:
        error(10, "Impass database error: {}".format(e.msg))
    log("New entry writen.")


def replace(args):
    """Replace password for entry.

    If the context does not already exist in the database an error
    will be thrown.

    """
    parser = argparse.ArgumentParser(prog=PROG+' replace',
                                     description=replace.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, ':' for prompt, or '-' for stdin")
    parser.add_argument('pwspec', nargs='?', action=PasswordAction,
                        help="password spec: N octets or ':' for prompt")
    if args is None: return parser
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    context = retrieve_context(args.context, db=db)
    if context not in db:
        error(2, "Context '{}' not found.".format(context))

    password = retrieve_password(args.pwspec)

    try:
        db.replace(context, password)
        db.save()
    except DatabaseError as e:
        error(10, "Impass database error: {}".format(e.msg))
    log("Password replaced.")


def update(args):
    """Update context for existing entry, keeping password the same.

    Special context value of '-' can only be provided to the old
    context.

    """
    parser = argparse.ArgumentParser(prog=PROG+' update',
                                     description=update.__doc__)
    parser.add_argument('old_context', nargs='?',
                        help="existing database context, ':' for prompt, or '-' for stdin")
    parser.add_argument('new_context', nargs='?',
                        help="new database context or ':' for prompt")
    if args is None: return parser
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    old_context = retrieve_context(args.old_context, prompt='old context: ', db=db)
    if old_context not in db:
        error(2, "Context '{}' not found".format(old_context))

    new_context = retrieve_context(args.new_context, prompt='new context: ', default=old_context, stdin=False)
    if new_context in db:
        error(2, "Context '{}' already exists.".format(new_context))

    try:
        db.update(old_context, new_context)
        db.save()
    except DatabaseError as e:
        error(10, "Impass database error: {}".format(e.msg))
    log("Entry updated.")


def dump(args):
    """Dump password database to stdout as json.

    If a string is provide only entries whose context contains the
    string will be dumped. Otherwise all entries are returned.
    Passwords will not be displayed unless IMPASS_DUMP_PASSWORDS is
    set.

    """
    parser = argparse.ArgumentParser(prog=PROG+' dump',
                                     description=dump.__doc__)
    parser.add_argument('string', nargs='?',
                        help="substring match for contexts")
    if args is None: return parser
    args = parser.parse_args(args)
    keyid = get_keyid()
    db = open_db(keyid)
    results = db.search(args.string)
    output = {}
    for context in results:
        output[context] = {}
        output[context]['date'] = results[context]['date']
        if os.getenv('IMPASS_DUMP_PASSWORDS'):
            output[context]['password'] = results[context]['password']
    print(json.dumps(output, sort_keys=True, indent=2))


def gui(args, method=os.getenv('IMPASS_XPASTE', 'xdo')):
    """Launch minimal X GUI.

    Good for X11 window manager integration. Upon invocation the user
    will be prompted to decrypt the database, after which a graphical
    search prompt will be presented. If an additional string is
    provided, it will be added as the initial search string. All
    matching results for the query will be presented to the user.
    When a result is selected, the password will be retrieved
    according to the method specified by IMPASS_XPASTE. If no match
    is found, the user has the opportunity to generate and store a new
    password, which is then delivered via IMPASS_XPASTE.

    Note: contexts that have leading or trailing whitespace are not
    accessible through the GUI.

    """
    parser = argparse.ArgumentParser(prog=PROG+' gui',
                                     description=gui.__doc__)
    parser.add_argument('string', nargs='?',
                        help="substring match for contexts")
    if args is None: return parser
    args = parser.parse_args(args)
    from .gui import Gui
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
        error(1, "Unknown X paste method '{}'.".format(method))
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
    """Remove entry.

    If the context does not already exist in the database an error
    will be thrown.

    """
    parser = argparse.ArgumentParser(prog=PROG+' remove',
                                     description=remove.__doc__)
    parser.add_argument('context', nargs='?',
                        help="existing database context, ':' for prompt, or '-' for stdin")
    if args is None: return parser
    args = parser.parse_args(args)

    keyid = get_keyid()
    db = open_db(keyid)

    context = retrieve_context(args.context, db=db)
    if context not in db:
        error(2, "Context '{}' not found.".format(context))

    try:
        log("Really remove entry '{}'?".format(context))
        response = input("Type 'yes' to remove: ")
    except KeyboardInterrupt:
        error(-1)
    if response != 'yes':
        error(-1)

    try:
        db.remove(context)
        db.save()
    except DatabaseError as e:
        error(10, "Impass database error: {}".format(e.msg))
    log("Entry removed.")


def print_help(args):
    """Full usage or command help (also '-h' after command)."""
    parser = argparse.ArgumentParser(prog=PROG+' help',
                                     description=print_help.__doc__)
    if args is None: return parser
    # if no argument is provided print the full man page
    try:
        cmd  = args[0]
    except IndexError:
        print_manpage()
        return
    # otherwise assume the first argument is a command and print it's
    # help
    func = get_func(cmd)
    func(['-h'])


def version(args):
    """Print version."""
    parser = argparse.ArgumentParser(prog=PROG+' version',
                                     description=version.__doc__)
    if args is None: return parser
    print(__version__)

############################################################
# main

synopsis = """{prog} <command> [<args>...]""".format(prog=PROG)

# NOTE: double spaces are interpreted by text2man to be paragraph
# breaks.  NO DOUBLE SPACES.  Also two spaces at the end of a line
# indicate an element in a tag list.
def print_manpage():
    print("""
NAME
  {prog} - Simple and secure password management and retrieval system

SYNOPSIS
  {synopsis}

DESCRIPTION

  The password database is stored as a single json object, OpenPGP
  encrypted and signed, and written to local disk (see
  IMPASS_DB). The file is created upon addition of the first
  entry. Database entries are keyed by 'context'. During retrieval of
  passwords the database is decrypted and read into memory. Contexts
  are searched by sub-string match.

  Contexts can be any string. If a context string is not specified on
  the command line it can be provided at a prompt, which features tab
  completion for contexts already in the database. One may also
  specify a context of '-' to read the context from stdin, or ':' to
  force a prompt.

  Passwords are auto-generated by default with {octets} bytes of
  entropy. The number of octets can be specified with the
  IMPASS_PASSWORD environment variable or via the 'pwspec' optional
  argument to relevant commands. The length of the actually generated
  password will sometimes be longer than the specified bytes due to
  base64 encoding. If pwspec is ':' the user will be prompted for the
  password.

COMMANDS

{cmds}

SIGNATURES
    During decryption, OpenPGP signatures on the db file are checked
    for validity. If any of them are found to not be valid, a warning
    message will be written to stderr.

ENVIRONMENT
    IMPASS_DB  
        Path to impass database file. Default: ~/.impass/db

    IMPASS_KEYFILE  
        File containing OpenPGP key ID of database encryption
        recipient. Default: ~/.impass/keyid

    IMPASS_KEYID  
        OpenPGP key ID of database encryption recipient. This
        overrides IMPASS_KEYFILE if set.

    IMPASS_PASSWORD  
        See Passwords above.

    IMPASS_DUMP_PASSWORDS  
        Include passwords in dump when set.

    IMPASS_XPASTE  
        Method for password retrieval. Options are: 'xdo', which
        attempts to type the password into the window that had focus
        on launch, or 'xclip' which inserts the password in the X
        clipboard. Default: xdo

AUTHOR
    Jameson Graef Rollins <jrollins@finestructure.net>
    Daniel Kahn Gillmor <dkg@fifthhorseman.net>
""".format(prog=PROG,
           synopsis=synopsis,
           cmds=format_commands(man=True),
           octets=DEFAULT_NEW_PASSWORD_OCTETS).strip())


def format_commands(man=False):
    prefix = ' '*8
    wrapper = textwrap.TextWrapper(
        width=70,
        initial_indent=prefix,
        subsequent_indent=prefix,
        )
    with io.StringIO("some initial text data") as f:
        for name, func in CMDS.items():
            if man:
                parser = func(None)
                usage = parser.format_usage()[len('usage: impass '):].strip()
                desc = wrapper.fill('\n'.join([l.strip() for l in parser.description.splitlines() if l]))
                f.write("  {}  \n".format(usage))
                f.write(desc+'\n')
                f.write('\n')
            else:
                desc = func.__doc__.splitlines()[0]
                f.write("  {:15}{}\n".format(name, desc))
        output = f.getvalue()
    return output.rstrip()


CMDS = collections.OrderedDict([
    ('add', add),
    ('replace', replace),
    ('update', update),
    ('dump', dump),
    ('gui', gui),
    ('remove', remove),
    ('help', print_help),
    ('version', version),
    ])
ALIAS = {
    '--version': 'version',
    '--help': 'help',
    '-h': 'help',
    }


def get_func(cmd):
    """Retrieve the appropriate function from the command argument."""
    if cmd in ALIAS:
        cmd = ALIAS[cmd]
    try:
        return CMDS[cmd]
    except KeyError:
        log("Unknown command: {}".format(cmd))
        log("See 'help' for usage.")
        error(1)


def main():
    if len(sys.argv) < 2:
        log("Command not specified.")
        log("usage: {}".format(synopsis))
        log()
        log(format_commands())
        error(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    func = get_func(cmd)

    ### DEPRECATE: this is for the assword->impass transition
    if os.path.basename(sys.argv[0]) == 'assword':
        log("""WARNING: assword has been renamed "impass".  Please update your invocations.""")
    vfound = []
    for var in ['DB', 'KEYFILE', 'KEYID', 'PASSWORD', 'DUMP_PASSWORDS', 'XPASTE']:
        val = os.getenv('ASSWORD_'+var)
        if val:
            vfound.append(var)
            if not os.getenv('IMPASS_'+var):
                os.environ['IMPASS_'+var] = val
    if vfound:
        log("""WARNING: assword has been renamed "impass".  Please update your environment variables:""")
        for var in vfound:
            log("  ASSWORD_{var} -> IMPASS_{var}".format(var=var))
    assword_dir = os.path.join(os.path.expanduser('~'),'.assword')
    if os.path.exists(assword_dir) and \
       (not os.path.islink(assword_dir)) and \
       os.path.isdir(assword_dir) and \
       (not os.getenv('IMPASS_DB')) and \
       cmd not in ['help', 'version', '-h', '--help', '--version']:
        try:
            os.rename(assword_dir, IMPASS_DIR)
            linkok = False
            try:
                os.symlink(IMPASS_DIR, assword_dir)
                linkok = True
            except:
                pass
            print("renamed ~/.assword -> ~/.impass", file=sys.stderr)
            if not linkok:
                print("(tried to symlink ~/.assword to ~/.impass as well, but symlinking failed)", file=sys.stderr)
        except:
            sys.exit("Could not rename old assword directory ~/.assword -> ~/.impass.\nPlease check ~/.impass path.")
        os.symlink(IMPASS_DIR, assword_dir)
        log("renamed ~/.assword -> ~/.impass")
    ### DEPRECATE

    cmd = sys.argv[1]
    args = sys.argv[2:]
    func = get_func(cmd)
    func(args)


if __name__ == "__main__":
    main()
