import os
import tempfile

# Must be set before any app import so the lazy engine binds to a throwaway DB.
_tmpdir = tempfile.mkdtemp(prefix="brainvc-test-")
os.environ["BRAINVC_DB"] = f"sqlite:///{_tmpdir}/test.db"
