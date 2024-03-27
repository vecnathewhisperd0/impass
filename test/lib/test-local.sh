# declare prerequisites for external binaries used in tests
# test_declare_external_prereq python3

export LC_ALL=C.UTF-8
export SRC_DIRECTORY=$(cd "$TEST_DIRECTORY"/.. && pwd)
export PYTHONPATH="$SRC_DIRECTORY":"$PYTHONPATH"
export IMPASS_DB="$TMP_DIRECTORY"/db
export GNUPGHOME="$TEST_DIRECTORY"/gnupg
export IMPASS_KEYID=84DCED32C1D6E9DDF52C65D1B2D1C2C1E7EEC6DC

impass() {
    python3 -m impass "$@"
}
