"""测试夹具：默认以管理员身份放行写端点鉴权。

写/审批端点上线了会话令牌守卫（require_role → get_principal）。为免逐请求登录取令牌，
这里用 FastAPI dependency_overrides 把唯一的 get_principal 覆盖为固定 admin 主体——
这是 FastAPI 推荐的测试缝，不削弱生产鉴权（生产无此 override）。

真实鉴权拦截（401/403）由 tests/test_auth.py 单独验证（它会临时移除该 override）。
"""

from __future__ import annotations

import pytest

from aisecops.L01_human_interface.api import app
from aisecops.L01_human_interface.auth_deps import get_principal
from aisecops.L02_agents import Principal


@pytest.fixture(autouse=True)
def _auth_as_admin():
    app.dependency_overrides[get_principal] = lambda: Principal(username="admin", role="管理员")
    yield
    app.dependency_overrides.pop(get_principal, None)
