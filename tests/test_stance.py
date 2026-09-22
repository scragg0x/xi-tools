"""Stance plumbing that needs no game files."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from xi.gear import xi_pose
from xi.gear.xi_pose import PoseSource
from xi.gear.xi_stance import stance_clips


def test_a_stance_nobody_defined_is_refused():
    with pytest.raises(ValueError):
        stance_clips([], "HumeMale", "cartwheel")


def test_stowed_melee_weapons_keep_their_own_grip(monkeypatch):
    monkeypatch.setattr(xi_pose, "parse_info", lambda data, sections: {
        "weapon_animation_type": 1, "standard_joint_index": 3, "scale": None})
    references = [SimpleNamespace(joint_index=100 + i) for i in range(xi_pose.HAND_REF_RIGHT + 1)]
    sources = [PoseSource(path=Path("main.dat"), slot="main"),
               PoseSource(path=Path("sub.dat"), slot="sub")]

    drawn, _ = xi_pose._weapon_overrides(sources, references, draw_ranged=False)
    stowed, _ = xi_pose._weapon_overrides(sources, references, draw_ranged=False,
                                          draw_melee=False)
    assert drawn
    assert stowed == {}
