"""SSRF protection: block private/loopback IPs and dangerous schemes."""
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status

BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript"}

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    # shared address space
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # ULA
    ipaddress.ip_network("fe80::/10"),        # link-local IPv6
]


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in PRIVATE_NETWORKS)
    except ValueError:
        return False


def check_url(url: str) -> None:
    """Raise HTTPException 400 if URL fails SSRF / scheme checks."""
    parsed = urlparse(url)

    if parsed.scheme in BLOCKED_SCHEMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scheme '{parsed.scheme}' is not allowed",
        )

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only http:// and https:// URLs are supported",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hostname")

    # Check hostname == localhost / 127.0.0.1 style strings directly
    if hostname.lower() in ("localhost", "localhost."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSRF: private address blocked")

    # Resolve hostname to IP(s) and check each
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            if _is_private_ip(ip):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SSRF: private/loopback address blocked ({ip})",
                )
    except HTTPException:
        raise
    except OSError:
        # DNS resolution failed — block to be safe
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSRF: hostname resolution failed")
