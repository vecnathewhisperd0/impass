import os
import io
import stat
import json
import time
import gpg  # type: ignore
import codecs
import datetime

from typing import Optional, Dict, Iterator

############################################################

DEFAULT_NEW_PASSWORD_OCTETS = 18


def pwgen(nbytes: int) -> str:
    """Return *nbytes* bytes of random data, base64-encoded."""
    s = os.urandom(nbytes)
    b = codecs.encode(s, "base64")
    b = bytes(filter(lambda x: x not in b"=\n", b))
    return codecs.decode(b, "ascii")


############################################################


class DatabaseError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)


class Database:
    """An impass database."""

    def __init__(
        self, dbpath: Optional[str] = None, keyid: Optional[str] = None
    ) -> None:
        """Database at dbpath will be decrypted and loaded into memory.

        If dbpath is not specified, an empty database will be
        initialized.

        The sigvalid property is set False if any OpenPGP signatures
        on the db file are invalid.  sigvalid is None for new
        databases.

        """
        self._dbpath = dbpath
        self._keyid = keyid

        # default database information
        self._type = "impass"
        self._version = 1
        self._entries: Dict[str, Dict[str, str]] = {}

        self._gpg = gpg.Context()
        self._gpg.armor = True
        self._sigvalid: Optional[bool] = None

        if self._dbpath and os.path.exists(self._dbpath):
            try:
                cleardata = self._decryptDB(self._dbpath)
                # FIXME: trap exception if json corrupt
                jsondata = json.loads(cleardata.decode("utf-8"))
            except IOError as e:
                raise DatabaseError(str(e))

            # unpack the json data
            # FIXME: we accept "assword" type for backwords compatibility
            if "type" not in jsondata or jsondata["type"] not in [
                self._type,
                "assword",
            ]:
                raise DatabaseError("Database is not a proper impass database.")
            if "version" not in jsondata or jsondata["version"] != self._version:
                raise DatabaseError("Incompatible database.")
            self._entries = jsondata["entries"]

    @property
    def version(self) -> int:
        """Database version."""
        return self._version

    @property
    def sigvalid(self) -> Optional[bool]:
        """Validity of OpenPGP signature on db file."""
        return self._sigvalid

    def __str__(self) -> str:
        return '<impass.Database "%s">' % (self._dbpath)

    def __repr__(self) -> str:
        return 'impass.Database("%s")' % (self._dbpath)

    def __getitem__(self, context: str) -> Dict[str, str]:
        """Return database entry for exact context."""
        return self._entries[context]

    def __contains__(self, context: str) -> bool:
        """True if context string in database."""
        return context in self._entries

    def __iter__(self) -> Iterator[str]:
        """Iterator of all database contexts."""
        return iter(self._entries)

    def _decryptDB(self, path: str) -> bytes:
        data = None
        self._sigvalid = False
        with open(path, "rb") as f:
            try:
                data, _, vfy = self._gpg.decrypt(f, verify=True)
                for s in vfy.signatures:
                    if s.validity >= gpg.constants.VALIDITY_FULL:
                        self._sigvalid = True
            except:
                # retry decryption without verification:
                with open(path, "rb") as try2:
                    data, _, _ = self._gpg.decrypt(try2, verify=False)
        if not isinstance(data, bytes):
            raise DatabaseError(
                f"expected gpg.Context.decrypt() to return bytes, got {type(data)}"
            )
        return data

    def _encryptDB(self, data: io.BytesIO, keyid: Optional[str]) -> bytes:
        # The signer and the recipient are assumed to be the same.
        # FIXME: should these be separated?
        try:
            recipient = self._gpg.get_key(keyid or self._keyid, secret=False)
            signer = self._gpg.get_key(keyid or self._keyid, secret=False)
        except:
            raise DatabaseError("Could not retrieve GPG encryption key.")
        self._gpg.signers = [signer]
        data.seek(0)
        encdata, _, _ = self._gpg.encrypt(
            data, [recipient], always_trust=True, compress=False
        )
        if not isinstance(encdata, bytes):
            raise DatabaseError(
                f"expected gpg.Context.decrypt() to return bytes, got {type(data)}"
            )
        return encdata

    def _set_entry(
        self, context: str, password: Optional[str] = None
    ) -> Dict[str, str]:
        if not isinstance(password, str):
            if password is None:
                bytes = DEFAULT_NEW_PASSWORD_OCTETS
            if isinstance(password, int):
                bytes = password
            password = pwgen(bytes)
        e = {"password": password, "date": datetime.datetime.utcnow().isoformat() + "Z"}
        self._entries[context] = e
        return e

    def add(self, context: str, password: Optional[str] = None) -> Dict[str, str]:
        """Add new entry.

        If password is None, one will be generated automatically.  If
        password is an int it will be interpreted as the number of
        random bytes to use.

        If the context is already in the db a DatabaseError will be
        raised.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if context == "":
            raise DatabaseError("Can not add empty string context")
        if context in self:
            raise DatabaseError("Context already exists (see replace())")
        return self._set_entry(context, password)

    def replace(self, context: str, password: Optional[str] = None) -> Dict[str, str]:
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

    def update(self, old_context: str, new_context: str) -> None:
        """Update entry context.

        If the old context is not in the db a DatabaseError will be
        raised.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if old_context not in self:
            raise DatabaseError("Context '%s' not found." % old_context)
        password = self[old_context]["password"]
        self.add(new_context, password)
        self.remove(old_context)

    def remove(self, context: str) -> None:
        """Remove entry.

        Database changes are not saved to disk until the save() method
        is called.

        """
        if context not in self:
            raise DatabaseError("Context '%s' not found" % context)
        del self._entries[context]

    def save(self, keyid: Optional[str] = None, path: Optional[str] = None) -> None:
        """Save database to disk.

        Key ID must either be specified here or at database initialization.
        If path not specified, database will be saved at original dbpath location.

        """
        # FIXME: should check that recipient is not different than who
        # the db was originally encrypted for
        if not keyid:
            keyid = self._keyid
        if not keyid:
            raise DatabaseError("Key ID for decryption not specified.")
        if not path:
            path = self._dbpath
        if not path:
            raise DatabaseError("Save path not specified.")
        jsondata = {
            "type": self._type,
            "version": self._version,
            "entries": self._entries,
        }
        cleardata = io.BytesIO(json.dumps(jsondata, indent=2).encode("utf-8"))
        encdata = self._encryptDB(cleardata, keyid)
        newpath = path + ".new"
        bakpath = path + ".bak"
        mode = stat.S_IRUSR | stat.S_IWUSR
        with open(newpath, "wb") as f:
            f.write(encdata)
        if os.path.exists(path):
            mode = os.stat(path)[stat.ST_MODE]
            os.rename(path, bakpath)
        # FIXME: shouldn't this be done when we're actually creating
        # the file?
        os.chmod(newpath, mode)
        os.rename(newpath, path)

    def search(self, string: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Search for string in contexts.

        If query is None, all entries will be returned.

        """
        mset = {}
        for context, entry in self._entries.items():
            # simple substring match
            if not string or string in context:
                mset[context] = entry
        return mset
