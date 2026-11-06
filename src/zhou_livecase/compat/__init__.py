"""Compatibility boundary for the verified v0.4.2 production runtime.

The portable package deliberately does not contain credentials or reimplement
the legacy COS/Feishu writers.  This package only normalizes their already
verified readback into the portable runner's receipt contract.
"""

from .v042 import LegacyStageAdapter, V042StageBridge

__all__ = ("LegacyStageAdapter", "V042StageBridge")
