"""L12 · 出站网络安全（C-22 出站白名单 / 防 SSRF）。

横切支撑：L05 网关与 L06 外发/连通测试共用同一套"这个 URL 能不能发"的判定，
避免各层各写一份字符串前缀判断（曾把 `10.example.com` 这种主机名误判为内网）。

两件事：
1. **出域判定** `is_outbound_url`：数据是否离开内网（决定是否脱敏/受出域开关约束）。
   用 `ipaddress` 精确判 IP 字面量；主机名一律视为出域（除非显式 localhost）。
2. **SSRF 防护** `ssrf_guard`：真正发 HTTP 前，把目标解析成 IP，拒绝指向内网/回环/
   链路本地（含云元数据 169.254.169.254）/保留地址的请求，除非命中显式白名单。
   - 外发 webhook（vendors 出域）：默认连内网都拒（allow_private=False）。
   - 连通测试内部数据源（ES/SIEM 多在内网）：allow_private=True，但仍拒链路本地/元数据。
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

_LOCAL_NAMES = {"localhost"}


def outbound_allowlist() -> set[str]:
    """出站白名单（host 或 IP），来自环境变量 AISECOPS_OUTBOUND_ALLOWLIST（逗号分隔）。

    用于显式放行"内网但可信"的目标（如内部企业微信代理）。不配则为空 = 不放行任何内网。
    """
    raw = os.environ.get("AISECOPS_OUTBOUND_ALLOWLIST", "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _resolve_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """把主机解析成 IP 列表；字面量 IP 直接返回，主机名走 DNS。解析失败返回空。"""
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return []
    out: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        try:
            out.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    return out


def _is_internal(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_private: bool) -> bool:
    """该 IP 是否应被出站拒绝。allow_private=True 时放行私网/回环，仅拒永不合法的目标。"""
    # 这些目标对外发/探测都没有合法理由：链路本地(含云元数据)、组播、未指定、保留段
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True
    if allow_private:
        return False
    return ip.is_private or ip.is_loopback


def is_outbound_url(url: str) -> bool:
    """True 表示该 URL 指向外部（出域，需脱敏 + 受出域开关约束，C-32）。"""
    host = (urlparse(url).hostname or "").lower()
    if not host or host in _LOCAL_NAMES:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # 主机名：视为出域（不再用 startswith 把 10.example.com 误判为内网）
        return True
    return not (ip.is_private or ip.is_loopback)


def ssrf_guard(url: str, *, allow_private: bool = False) -> tuple[bool, str]:
    """发 HTTP 前的 SSRF 校验。返回 (是否放行, 拒绝原因)。

    Args:
        url: 目标地址。
        allow_private: 是否允许私网/回环（连通测试内部数据源用 True；外发 webhook 用 False）。
    """
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False, "URL 缺少主机名"
    allow = outbound_allowlist()
    if host in allow:
        return True, ""
    ips = _resolve_ips(host)
    if not ips:
        return False, f"无法解析主机 {host}"
    for ip in ips:
        if str(ip) in allow:
            continue
        if _is_internal(ip, allow_private=allow_private):
            kind = "内网/回环" if (ip.is_private or ip.is_loopback) else "链路本地/元数据/保留"
            return False, f"目标 {host}→{ip} 属{kind}地址，已拒绝（防 SSRF，C-22）"
    return True, ""
