#!/usr/bin/env python3
"""Phase 19 test matrix: aggregates Parts A-N coverage in a single run.

Each imported module is a hermetic-or-live unittest suite from the Phase 19
plan. This file adds no new assertions; it exists so the whole phase can be
run with one command:

    python3 -m unittest test_phase19_matrix
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_phase19_bsk_census  # Part A  # noqa: E402,F401
import test_phase19_bsk_semantics  # Part B  # noqa: E402,F401
import test_phase19_weights  # Part C  # noqa: E402,F401
import test_phase19_skeleton  # Part D  # noqa: E402,F401
import test_phase19_bsr_chain  # Part E  # noqa: E402,F401
import test_phase19_anim_census  # Part F  # noqa: E402,F401
import test_phase19_animation  # Part G  # noqa: E402,F401
import test_phase19_pose  # Part H  # noqa: E402,F401
import test_phase19_skinned_mesh  # Part I  # noqa: E402,F401
import test_phase19_real_npc  # Part J  # noqa: E402,F401
import test_phase19_real_animation  # Part K  # noqa: E402,F401
import test_phase19_player  # Part L  # noqa: E402,F401

_MODULES = (
    test_phase19_bsk_census,
    test_phase19_bsk_semantics,
    test_phase19_weights,
    test_phase19_skeleton,
    test_phase19_bsr_chain,
    test_phase19_anim_census,
    test_phase19_animation,
    test_phase19_pose,
    test_phase19_skinned_mesh,
    test_phase19_real_npc,
    test_phase19_real_animation,
    test_phase19_player,
)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for mod in _MODULES:
        suite.addTests(loader.loadTestsFromModule(mod))
    return suite


if __name__ == "__main__":
    unittest.main()
