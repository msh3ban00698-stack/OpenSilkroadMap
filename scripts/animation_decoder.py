#!/usr/bin/env python3
"""Phase 19 animation decoder facade (Part G/H).

The proven BAN decoder lives in ban_decoder.py / animation_pose.py; this
module is a stable entry point exposing the Phase 19 describe/evaluate API:
  * describe_animation(raw) -> proven clip facts (Part G)
  * load_keyframes(raw)     -> per-bone keyframe lists
  * evaluate_pose(...)      -> deterministic pose evaluation (Part H)
"""
from __future__ import annotations

from animation_pose import (  # noqa: F401
    KEYFRAME_STRIDE,
    describe_animation,
    evaluate_pose,
    load_keyframes,
)
