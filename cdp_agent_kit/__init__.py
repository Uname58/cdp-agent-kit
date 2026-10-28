"""cdp-agent-kit — Let AI agents control your browser via Chrome DevTools Protocol."""

from cdp_agent_kit.cdp import (
    CDPClient,
    CDPError,
    CDPConnError,
    launch_chrome,
    wait_for_cdp,
    resolve_cdp_host,
    ensure_cdp,
)

try:
    from cdp_agent_kit.bridge import CDPBridge, ElementSnapshot
except ImportError:
    # playwright 是可选依赖（通用工具层），未安装时 bridge 降级为 None
    CDPBridge = None
    ElementSnapshot = None

__version__ = "0.2.0"
__all__ = [
    "CDPClient",
    "CDPError",
    "CDPConnError",
    "launch_chrome",
    "wait_for_cdp",
    "resolve_cdp_host",
    "ensure_cdp",
    "CDPBridge",
    "ElementSnapshot",
]
