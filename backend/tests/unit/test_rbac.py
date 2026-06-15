from types import SimpleNamespace

import pytest

from src.core.deps import ROLE_RANK, TenantCtx
from src.core.exceptions import Forbidden


def _ctx(role: str) -> TenantCtx:
    return TenantCtx(db=None, user=None, membership=SimpleNamespace(role=role, id="m1"))


def test_role_ranking_order():
    assert ROLE_RANK["admin"] > ROLE_RANK["manager"] > ROLE_RANK["collaborator"] > ROLE_RANK["guest"]


def test_require_allows_equal_or_higher():
    _ctx("manager").require("manager")  # igual — ok
    _ctx("admin").require("manager")  # superior — ok
    _ctx("manager").require("collaborator")  # superior — ok


def test_require_blocks_lower():
    with pytest.raises(Forbidden):
        _ctx("collaborator").require("manager")
    with pytest.raises(Forbidden):
        _ctx("guest").require("admin")


def test_role_property():
    assert _ctx("admin").role == "admin"
