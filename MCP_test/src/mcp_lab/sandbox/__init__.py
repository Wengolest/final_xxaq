"""MCP 投毒实验沙箱：虚拟文件系统、外泄捕获、敏感文件 fixture。"""

from .filesystem import SandboxFS
from .exfil_sink import ExfilSink
from .seed_fixtures import seed_sandbox

__all__ = ["SandboxFS", "ExfilSink", "seed_sandbox"]
