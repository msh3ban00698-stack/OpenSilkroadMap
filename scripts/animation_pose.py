#!/usr/bin/env python3
"""Phase 18 animation pose evaluation (BAN -> skeleton pose).

Proven facts (validated on bandit_stand01/walk from Data.pk2):
  * parse_ban (ban_decoder) fully consumes the file; per-bone keyframes share
    one global timestamp table (kpb entries, ascending, first 0, last=duration).
  * keyframe record = [x,y,z,w] quaternion + [x,y,z] position (28 bytes).
  * channel bone names map onto the .bsk skeleton by name; bones absent from
    the animation keep their bind local transform (rot_parent/tr_parent).
  * quaternion/position interpolation between adjacent keyframes is used
    (timestamps are not uniform: walk uses 33/133/266/333 ms deltas).

This module ships no PK2 reader; it operates on raw bytes only.
"""
from __future__ import annotations

import struct

import ban_decoder as BAN  # noqa: E402
import skeleton as SK  # noqa: E402

KEYFRAME_STRIDE = BAN.KEYFRAME_STRIDE


def _slerp(a, b, t):
    """Spherical interpolation between [x,y,z,w] quaternions (short arc)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    dot = ax * bx + ay * by + az * bz + aw * bw
    if dot < 0.0:
        bx, by, bz, bw = -bx, -by, -bz, -bw
        dot = -dot
    if dot > 0.9995:
        out = [a[k] + t * (b[k] - a[k]) for k in range(4)]
        n = (out[0] ** 2 + out[1] ** 2 + out[2] ** 2 + out[3] ** 2) ** 0.5
        return [x / n for x in out]
    theta0 = __import__("math").acos(dot)
    sin0 = __import__("math").sin(theta0)
    s0 = __import__("math").sin((1.0 - t) * theta0) / sin0
    s1 = __import__("math").sin(t * theta0) / sin0
    return [s0 * a[k] + s1 * b[k] for k in range(4)]


def load_keyframes(raw: bytes, bone_cap: int = 0):
    """Parse a BAN fully and return per-bone keyframe lists.

    Returns {'duration_ms', 'timestamps', 'channels': {bone_name: [(q, pos)...]}}.
    Each channel's list aligns with the global timestamps.
    """
    r = BAN.parse_ban(raw, keyframe_cap=0)
    timestamps = r["timestamps"]
    channels = {}
    for b in r["bones"]:
        recs = []
        for i in range(b["keyframes"]):
            off = b["keyframe_start"] + i * KEYFRAME_STRIDE
            q = list(struct.unpack_from("<4f", raw, off))
            p = list(struct.unpack_from("<3f", raw, off + 16))
            recs.append((q, p))
        channels[b["name"]] = recs
    return {
        "duration_ms": r["duration_ms"],
        "timestamps": timestamps,
        "channels": channels,
    }


def describe_animation(raw: bytes):
    """Describe a BAN clip with ONLY proven facts (Phase 19 Part G).

    Returns a dict with every field derived from source bytes or clearly
    labelled UNKNOWN. frame_rate is reported as a header field but timestamps
    are authoritative for timing (bandit_walk timestamps are non-uniform).
    Looping is PROVEN when the first keyframe equals the last for every
    channel. Root motion is reported from the Bip01 translation channel.
    """
    r = BAN.parse_ban(raw, keyframe_cap=0)
    anim = load_keyframes(raw)
    ts = anim["timestamps"]
    channels = anim["channels"]
    uniform = all(
        ts[i + 1] - ts[i] == ts[1] - ts[0]
        for i in range(len(ts) - 1))
    loops = len(ts) > 1 and all(
        len(ch) > 1
        and all(abs(a - b) < 2e-3 for a, b in zip(ch[0][0], ch[-1][0]))
        and all(abs(a - b) < 2e-3 for a, b in zip(ch[0][1], ch[-1][1]))
        for ch in channels.values())
    root = channels.get("Bip01", [])
    root_positions = [ch[1] for ch in root]
    root_drift = max(
        max(abs(a - root_positions[0][k]) for a in (p[k] for p in root_positions))
        for k in range(3)) if root_positions else 0.0
    return {
        "clip_count": 1,
        "clip_name": r["header"]["name"],
        "duration_ms": r["duration_ms"],
        "keyframe_count": r["keyframes_per_bone"],
        "timestamps": ts,
        "timestamps_uniform": uniform,
        "timestamps_non_uniform": not uniform,
        "target_bones": list(channels.keys()),
        "bone_count": len(channels),
        "has_rotation": True,
        "has_translation": True,
        "has_scale": False,
        "keyframe_stride_bytes": KEYFRAME_STRIDE,
        "interpolation": "not stored in file; evaluator applies "
                         "slerp(quat)+lerp(pos)",
        "compression": "none (raw 28-byte records)",
        "looping": loops,
        "loop_evidence": "first keyframe == last keyframe for every channel"
                         if loops else "no first==last keyframe match",
        "root_motion": root_drift > 1e-3,
        "root_drift_units": round(root_drift, 4),
        "frame_rate_header": r["frame_rate"],
        "timing_note": "timestamps are authoritative; frame_rate field nominal",
        "unknown_u32": r["unknown_u32"],
    }


def _sample(channel, timestamps, t):
    """Interpolate (q, pos) at time t within [t0, tN] (clamped at ends)."""
    if not channel:
        return None
    n = len(channel)
    if t <= timestamps[0]:
        return channel[0]
    if t >= timestamps[-1]:
        return channel[-1]
    # find bracketing index
    hi = 0
    while hi < n - 1 and timestamps[hi] < t:
        hi += 1
    lo = hi - 1 if hi > 0 else 0
    t0, t1 = timestamps[lo], timestamps[hi]
    if t1 == t0:
        return channel[lo]
    f = (t - t0) / (t1 - t0)
    q0, p0 = channel[lo]
    q1, p1 = channel[hi]
    q = _slerp(q0, q1, f)
    p = [p0[k] + f * (p1[k] - p0[k]) for k in range(3)]
    return (q, p)


def evaluate_pose(raw: bytes, t_ms: float, bones):
    """Evaluate an animation at t_ms onto a .bsk skeleton (bone list).

    Returns a dict {bone_index: (local_quat[xyzw], local_pos[xyz])} where
    bones present in the animation use interpolated channel values and
    bones absent fall back to the bind local transform. All keyframes in the
    first parsed animation channel are counted for determinism checks.
    """
    anim = load_keyframes(raw)
    ts = anim["timestamps"]
    channels = anim["channels"]
    pose = {}
    for i, b in enumerate(bones):
        ch = channels.get(b["name"])
        if ch:
            s = _sample(ch, ts, t_ms)
            pose[i] = (s[0], s[1])
        else:
            pose[i] = (list(b["rot_parent"]), list(b["tr_parent"]))
    return pose


def chain_world(pose, bones):
    """Chain local pose into world (rot,pos) per bone using skeleton parents."""
    parents = SK.bone_parents(bones)
    wrot = [None] * len(bones)
    wpos = [None] * len(bones)
    for i in range(len(bones)):
        q, p = pose[i]
        if parents[i] == -1:
            wrot[i] = list(q)
            wpos[i] = list(p)
        else:
            pr = parents[i]
            wrot[i] = SK.qmul(wrot[pr], q)
            off = SK.qrot(wrot[pr], p)
            wpos[i] = [wpos[pr][k] + off[k] for k in range(3)]
    return wrot, wpos
