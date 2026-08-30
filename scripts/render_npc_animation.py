#!/usr/bin/env python3
"""Phase 19 Part K deterministic pose renderer (bandit NPC).

Renders the REAL bandit skeleton posed by a REAL BAN clip at a fixed
timestamp into a deterministic SVG snapshot (bone chain as line segments,
joints as dots). The snapshot is byte-identical for identical inputs, and the
returned per-bone world transforms let a test prove the animation genuinely
moves the skeleton away from its bind pose.

No PK2 reader here: inputs are raw BSK bytes, raw BAN bytes, and the resolved
bone list. The skeleton is chained from the BAN channels (which replace the
bind rot_parent/tr_parent, Phase 19 PROVEN) with bind fallback for bones the
clip does not animate.

Usage:  python3 scripts/render_npc_animation.py \
            --bsk <bandit.bsk> --ban <bandit_walk.ban> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import os

import bsk_decoder as BSK  # noqa: E402
import skeleton as SK  # noqa: E402
import animation_pose as AP  # noqa: E402

FRONT = "front"
SIDE = "side"

VIEW_SCALE = 12.0
VIEW_HALF = 400.0


def _project(pos, view):
    if view == SIDE:
        sx = VIEW_HALF + pos[2] * VIEW_SCALE
        sy = VIEW_HALF - pos[1] * VIEW_SCALE
    else:
        sx = VIEW_HALF + pos[0] * VIEW_SCALE
        sy = VIEW_HALF - pos[1] * VIEW_SCALE
    return sx, sy


def _svg(bones, world_pos, view):
    lines = []
    for i, b in enumerate(bones):
        x, y = _project(world_pos[i], view)
        lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3"/>')
    parents = SK.bone_parents(bones)
    for i in range(len(bones)):
        if parents[i] != -1:
            x0, y0 = _project(world_pos[parents[i]], view)
            x1, y1 = _project(world_pos[i], view)
            lines.append(
                f'<line x1="{x0:.2f}" y1="{y0:.2f}" '
                f'x2="{x1:.2f}" y2="{y1:.2f}" stroke="#000"/>')
    body = "".join(lines)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="800" height="800" viewBox="0 0 800 800">'
        f'<rect width="800" height="800" fill="#fff"/>'
        f'<g stroke="#000" stroke-width="1.5" fill="#000">{body}</g>'
        f"</svg>"
    )


def render_npc_pose(bones, ban_bytes, t_ms, view=FRONT):
    """Pose the skeleton at t_ms and return a deterministic snapshot + facts.

    Returns {svg, sha256, t_ms, bone_world_pos, bind_world_pos, max_deviation}.
    """
    pose = AP.evaluate_pose(ban_bytes, t_ms, bones)
    _, world_pos = AP.chain_world(pose, bones)
    _, bind_pos = SK.bind_world(bones)
    max_dev = max(
        (sum((world_pos[i][k] - bind_pos[i][k]) ** 2 for k in range(3)) ** 0.5)
        for i in range(len(bones)))
    svg = _svg(bones, world_pos, view)
    return {
        "svg": svg,
        "sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest(),
        "t_ms": t_ms,
        "view": view,
        "bone_world_pos": [[round(x, 6) for x in p] for p in world_pos],
        "bind_world_pos": [[round(x, 6) for x in p] for p in bind_pos],
        "max_deviation_from_bind": round(max_dev, 6),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bsk", required=True)
    ap.add_argument("--ban", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--view", choices=(FRONT, SIDE), default=FRONT)
    ap.add_argument("--times", default="0,700,1333")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    with open(args.bsk, "rb") as fh:
        bones = BSK.parse_bsk(fh.read())["bones"]
    with open(args.ban, "rb") as fh:
        ban = fh.read()
    anim = AP.load_keyframes(ban)
    ts = [int(x) for x in args.times.split(",")]
    stem = os.path.basename(args.ban)[:-4]
    for t in ts:
        if t > anim["duration_ms"]:
            t = anim["duration_ms"]
        res = render_npc_pose(bones, ban, t, view=args.view)
        out = os.path.join(args.out, f"{stem}_{t}ms_{args.view}.svg")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(res["svg"])
        print(f"{out} sha256={res['sha256']} max_dev={res['max_deviation_from_bind']}")


if __name__ == "__main__":
    main()
