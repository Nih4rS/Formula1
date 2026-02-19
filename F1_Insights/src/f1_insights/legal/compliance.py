from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompliancePolicy:
    allow_live_timing_replication: bool = False
    allow_rebroadcast_stream: bool = False
    allow_direct_betting_feed: bool = False
    require_user_data_attestation: bool = True


DEFAULT_POLICY = CompliancePolicy()


ATTESTATION_TEXT = (
    "I confirm this upload comes from data I am legally allowed to use (my own export/sim data), "
    "and I will not use this app to replicate official live timing or rebroadcast proprietary content."
)


COMPLIANCE_BULLETS = [
    "Transformative analytics only: derived insights and comparisons.",
    "No full live timing tower replication.",
    "No proprietary stream rebroadcast.",
    "User-uploaded telemetry must be legally obtained by the user.",
    "Open mode uses public/community historical endpoints.",
]
