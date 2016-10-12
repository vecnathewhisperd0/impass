import os
import io
import stat
import json
import time
import pyme
import codecs
import datetime

############################################################

DEFAULT_NEW_PASSWORD_OCTETS = 18

def pwgen(nbytes):
    """Return *nbytes* bytes of random data, base64-encoded."""
    s = os.urandom(nbytes)
    b = codecs.encode(s, 'base64')
    b = bytes(filter(lambda x: x not in b'=\n', b))
    return codecs.decode(b, 'ascii')

############################################################

class DatabaseError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class Database:
    """An Assword database."""

    def __init__(self, dbpath=None, keyid=None):
        """Database at dbpath will be decrypted and loaded into memory.

        If dbpath not specified, empty database will be initialized.

        The sigvalid property is set False if any OpenPGP signatures
        on the db file are invalid.  sigvalid is None for new
        databases.

        """
        self._dbpath = dbpath
        self._keyid = keyid

        # default database information
        self._type = 'assword'
        self._version = 1
        self._entries = {}

        self._gpg = pyme.Context()
        self._gpg.armor = True
        self._sigvalid = None

        if self._dbpath and os.path.exists(self._dbpath):
            try:
                cleardata = self._decryptDB(self._dbpath)
                # FIXME: trap exception if json corrupt
                jsondata = json.loads(cleardata.decode('utf-8'))
            except IOError as e:
                raise DatabaseError(e)

            # unpack the json data
            if 'type' not in jsondata or jsondata['type'] != self._type:
                raise DatabaseError('Database is not a proper assword database.')
            if 'version' not in jsondata or jsondata['version'] != self._version:
                raise DatabaseError('Incompatible database.')
            self._entries = jsondata['entries']

    @property
    def version(self):
        """Database version."""
        return self._version

    @property
    def sigvalid(self):
        """Validity of OpenPGP signature on db file."""
        return self._sigvalid

    def __str__(self):
        return '<assword.Database "%s">' % (self._dbpath)

    def __repr__(self):
        return 'assword.Database("%s")' % (self._dbpath)

    def __getitem__(self, context):
        """Return database entry for exact context."""
        return self._entries[context]

    def __contains__(self, context):
        """True if context string in database."""
        return context in self._entries

    def __iter__(self):
        """Iterator of all database contexts."""
        return iter(self._entries)

    def _decryptDB(self, path):
        data = io.BytesIO()
        with io.BytesIO() as encdata:
            with open(path, 'rb') as f:
                encdata.write(f.read())
                encdata.seek(0)
                data, _, vfy = self._gpg.decrypt(encdata)
        # check signature
        if not vfy.signatures[0].validity >= pyme.constants.VALIDITY_FULL:
            self._sigvalid = False
        else:
            self._sigvalid = True
        return data

    def _encryptDB(self, data, keyid):
        # The signer and the recipient are assumed to be the same.
        # FIXME: should these be separated?
        try:
            recipient = self._gpg.get_key(keyid or self._keyid, secret=False)
            signer = self._gpg.get_key(keyid or self._keyid, secret=False)
        except:
            raise DatabaseError('Could not retrieve GPG encryption key.')
        self._gpg.signers = [signer]
        data.seek(0)
        encdata, _, _ = self._gpg.encrypt(data, [recipient],
                                          always_trust=True,
                                          compress=False)
        return encdata

    def _set_entry(self, context, password=None):
        if not isinstance(password, str):
            if password is None:
                bytes = DEFAULT_NEW_PASSWORD_OCTETS
            if isinstance(password, int):
                bytes = password
            password = pwgen(bytes)
        e = {'password': password,
             'date': datetime.datetime.now().isoformat()}
        self._entries[context] = e
        return e

    def add(self, context, password=None):
        """Add new entry.

        If password is None, one will be generated automatically.  If
        password is an int it will be interpreted as the number of
        random bytes to use.

        If the context is already in the db a DatabaseError will be
        raised.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if context == '':
            raise DatabaseError("Can not add empty string context")
        if context in self:
            raise DatabaseError("Context already exists (see replace())")
        return self._set_entry(context, password)

    def replace(self, context, password=None):
        """Replace entry password.

        If password is None, one will be generated automatically.  If
        password is an int it will be interpreted as the number of
        random bytes to use.

        If the context is not in the db a DatabaseError will be
        raised.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if context not in self:
            raise DatabaseError("Context not found (see add())")
        return self._set_entry(context, password)

    def update(self, old_context, new_context):
        """Update entry context.

        If the old context is not in the db a DatabaseError will be
        raised.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if old_context not in self:
            raise DatabaseError("Context '%s' not found." % old_context)
        password = self[old_context]['password']
        self.add(new_context, password)
        self.remove(old_context)

    def remove(self, context):
        """Remove entry.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if context not in self:
            raise DatabaseError("Context '%s' not found" % context)
        del self._entries[context]

    def save(self, keyid=None, path=None):
        """Save database to disk.

        Key ID must either be specified here or at database initialization.
        If path not specified, database will be saved at original dbpath location.

        """
        # FIXME: should check that recipient is not different than who
        # the db was originally encrypted for
        if not keyid:
            keyid = self._keyid
        if not keyid:
            raise DatabaseError('Key ID for decryption not specified.')
        if not path:
            path = self._dbpath
        if not path:
            raise DatabaseError('Save path not specified.')
        jsondata = {'type': self._type,
                    'version': self._version,
                    'entries': self._entries}
        cleardata = io.BytesIO(json.dumps(jsondata, indent=2).encode('utf-8'))
        encdata = self._encryptDB(cleardata, keyid)
        newpath = path + '.new'
        bakpath = path + '.bak'
        mode = stat.S_IRUSR | stat.S_IWUSR
        with open(newpath, 'wb') as f:
            f.write(encdata)
        if os.path.exists(path):
            mode = os.stat(path)[stat.ST_MODE]
            os.rename(path, bakpath)
        # FIXME: shouldn't this be done when we're actually creating
        # the file?
        os.chmod(newpath, mode)
        os.rename(newpath, path)

    def search(self, string=None):
        """Search for string in contexts.

        If query is None, all entries will be returned.

        """
        mset = {}
        for context, entry in self._entries.items():
            # simple substring match
            if not string or string in context:
                mset[context] = entry
        return mset
