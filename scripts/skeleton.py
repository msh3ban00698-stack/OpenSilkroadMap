#!/usr/bin/env python3
"""Phase 18 skeleton hierarchy + bind-pose reconstruction.

Proven convention (validated against bandit.bsk + its meshes):
  * quaternion fields are [x, y, z, w]
  * rot_parent/tr_parent are the local rotation/position of a bone relative
    to its parent; chaining parent->child yields the bind-pose world matrix.
    This is proven because the computed world positions land inside the
    mesh geometry: toe bone y~0.02 vs mesh ground y~0.03, hands at shoulder
    height inside the arm slab, pelvis mid-body.
  * tr_origin/rot_origin and tr_local/rot_local are exported verbatim
    (semantics UNKNOWN; not used for the bind world).
"""
from __future__ import annotations

import math


def qmul(a, b):
    """Multiply two [x,y,z,w] quaternions."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def qrot(q, v):
    """Rotate vector v by [x,y,z,w] quaternion q."""
    x, y, z, w = q
    vx, vy, vz = v
    cx = y * vz - z * vy
    cy = z * vx - x * vz
    cz = x * vy - y * vx
    return [
        vx + 2.0 * (w * cx + y * cz - z * cy),
        vy + 2.0 * (w * cy + z * cx - x * cz),
        vz + 2.0 * (w * cz + x * cy - y * cx),
    ]


def quat_is_unit(q, tol=1e-3):
    return abs(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2 - 1.0) < tol


def name_index(bones):
    return {b["name"]: i for i, b in enumerate(bones)}


def bone_parents(bones):
    """Return list of parent indices (-1 for root). Validates acyclicity."""
    index = name_index(bones)
    parents = []
    for i, b in enumerate(bones):
        if b["parent"] == "":
            parents.append(-1)
        else:
            if b["parent"] not in index:
                raise ValueError(
                    "bone %r parent %r not present" % (b["name"], b["parent"]))
            parents.append(index[b["parent"]])
    for i, p in enumerate(parents):
        seen = set()
        j = i
        while p != -1:
            if p in seen:
                raise ValueError("cycle detected at bone %d" % i)
            seen.add(p)
            j = p
            p = parents[j]
    return parents


def bind_world(bones):
    """Return (world_rot, world_pos) per bone in bind pose."""
    parents = bone_parents(bones)
    world_rot = [None] * len(bones)
    world_pos = [None] * len(bones)
    for i, b in enumerate(bones):
        if parents[i] == -1:
            world_rot[i] = list(b["rot_parent"])
            world_pos[i] = list(b["tr_parent"])
        else:
            p = parents[i]
            world_rot[i] = qmul(world_rot[p], b["rot_parent"])
            off = qrot(world_rot[p], b["tr_parent"])
            world_pos[i] = [world_pos[p][k] + off[k] for k in range(3)]
    return world_rot, world_pos


def validate_mesh_bones(skel_names, mesh_names):
    """Return the subset of mesh bone names missing from the skeleton."""
    s = set(skel_names)
    return [n for n in mesh_names if n not in s]


def world_positions(bones):
    """Convenience: per-bone world position dict keyed by bone name."""
    _, wp = bind_world(bones)
    return {b["name"]: wp[i] for i, b in enumerate(bones)}
