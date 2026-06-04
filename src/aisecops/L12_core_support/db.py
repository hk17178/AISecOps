"""L12 · PostgreSQL 连接池（P-18 持久化地基）。

横切支撑：任何层经此拿连接。按 database_url 缓存连接池。
"""

from __future__ import annotations

from psycopg_pool import ConnectionPool

_pools: dict[str, ConnectionPool] = {}


def get_pool(database_url: str) -> ConnectionPool:
    """取（或建）该 URL 的连接池。连不上会在此抛错，调用方决定回退。

    connect_timeout 限定单次连接尝试，open(timeout) 限定整体等待；
    连不上时快速失败并销毁池，避免后台线程持续重连。
    """
    pool = _pools.get(database_url)
    if pool is None:
        pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=4,
            open=False,
            kwargs={"connect_timeout": 3},
        )
        try:
            pool.open(wait=True, timeout=3)
        except Exception:
            pool.close()
            raise
        _pools[database_url] = pool
    return pool
