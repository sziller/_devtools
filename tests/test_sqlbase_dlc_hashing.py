"""Regression tests: DLC row-ID hashing uses only the standard library.

Background: sql_bases.sqlbase_dlc used to import `cryptography.HashFunctions`, a module that lives in the
separate `sziller_assist` wheel, which installs a top-level `cryptography/` package and clobbers PyPI's
`cryptography/__init__.py`. The hash is plain SHA-256, so hashlib is used directly.

The expected values below were produced independently with the `sha256sum` CLI (not with hashlib).
"""
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_bases.sqlbase_dlc.sqlbase_dlc import LendBorrowBTCXXX_Product  # noqa: E402


def _id_hash(tmp_cntr_id, created_at):
    # generate_id_hash only reads these two attributes, so no database/row construction is needed.
    return LendBorrowBTCXXX_Product.generate_id_hash(
        SimpleNamespace(tmp_cntr_id=tmp_cntr_id, created_at=created_at))


# (tmp_cntr_id, created_at, expected) -> expected = first 16 hex chars of sha256(f"{tmp_cntr_id}{created_at}")
VECTORS = [
    ("a", "bc", "ba7816bf8f01cfea"),                     # sha256("abc") = ba7816bf8f01cfea414140de...
    ("tmp_42_", 1700000000.5, "585ae84a84ce7fa9"),        # float timestamp is formatted with str()
    ("dlc-é✓", 1700000000.25, "7930e6c53a7e65bf"),        # non-ASCII is hashed as UTF-8
]


@pytest.mark.parametrize("tmp_cntr_id, created_at, expected", VECTORS)
def test_generate_id_hash_known_vectors(tmp_cntr_id, created_at, expected):
    result = _id_hash(tmp_cntr_id, created_at)
    assert result == expected
    assert len(result) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", result)


def test_generate_id_hash_is_deterministic_and_input_sensitive():
    assert _id_hash("x", 1.0) == _id_hash("x", 1.0)
    assert _id_hash("x", 1.0) != _id_hash("x", 2.0)


def test_sqlbase_dlc_imports_without_custom_hashfunctions_module():
    """Importing must not touch `cryptography.HashFunctions` (a None entry in sys.modules makes it fail)."""
    code = (
        "import sys; sys.modules['cryptography.HashFunctions'] = None; "
        f"sys.path.insert(0, {str(REPO_ROOT)!r}); "
        "import sql_bases.sqlbase_dlc.sqlbase_dlc as m; "
        "assert not hasattr(m, 'HaFu')"
    )
    proc = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_no_devtools_source_references_hashfunctions():
    offenders = []
    for path in (REPO_ROOT / "sql_bases").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "HashFunctions" in text or "HaFu" in text or "sziller_assist" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_devtools_does_not_ship_a_cryptography_namespace():
    assert not (REPO_ROOT / "cryptography").exists()
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert not re.search(r'^\s*"cryptography', pyproject, flags=re.MULTILINE)


def test_pypi_cryptography_unaffected():
    crypto = pytest.importorskip("cryptography")
    assert hasattr(crypto, "__version__")
    from cryptography.hazmat.primitives import hashes
    digest = hashes.Hash(hashes.SHA256())
    digest.update(b"abc")
    assert digest.finalize().hex().startswith("ba7816bf8f01cfea")
