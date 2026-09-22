"""Which clips ``merge_pose_clip`` picks for a given ``--anim`` — no game files needed."""

import pytest

from xi.entity.anim.xi_export import (
    SECTION_TYPE_SKELETON_ANIMATION,
    AnimationSection,
    Section,
)
from xi.gear import xi_pose


def section(name: str) -> Section:
    return Section(name=name, type_code=SECTION_TYPE_SKELETON_ANIMATION,
                   start=0, size=0, data_start=0)


@pytest.fixture
def pool(monkeypatch):
    """One DAT holding a clip family whose name ends in a digit, plus a plain one.

    Each stub clip drives a joint of its own plus the shared joint 9, so a merge is
    visible in the result and the last layer in wins what they share.
    """
    names = ["idl0", "idl1", "na10", "na11", "na20", "na21"]
    sections = [section(n) for n in names]

    def fake_parse(data, sec):
        return AnimationSection(name=sec.name, num_joints=71, num_frames=1,
                                keyframe_duration=1.0,
                                tracks={names.index(sec.name): sec.name, 9: sec.name})

    def fake_variants(data, base):
        # Same rule as the real one, off the stub names instead of DAT bytes.
        return sorted(n for n in names
                      if n == base or (n.startswith(base) and n[len(base):].isdigit()))

    monkeypatch.setattr(xi_pose, "parse_animation", fake_parse)
    monkeypatch.setattr(xi_pose, "animation_variants", fake_variants)
    return [(b"", sections)]


def merged(anim, pool):
    return xi_pose.merge_pose_clip(anim, pool, 71)


def test_digitless_name_merges_every_variant(pool):
    clip, layers = merged("idl", pool)
    assert layers == ["idl0", "idl1"]
    assert clip.name == "idl"


def test_name_ending_in_a_digit_is_one_layer(pool):
    clip, layers = merged("idl1", pool)
    assert layers == ["idl1"]
    assert clip.tracks[9] == "idl1"


def test_comma_separated_names_merge_exactly_those_clips(pool):
    clip, layers = merged("na10,na11", pool)
    assert layers == ["na10", "na11"]
    # Both variants' own joints survive — that is the point, the 16-joint variant
    # carries the legs and the 71-joint one the arms and weapon grips.
    assert clip.tracks[2] == "na10"
    assert clip.tracks[3] == "na11"
    # A joint both drive goes to the one named last.
    assert clip.tracks[9] == "na11"


def test_merged_clip_is_named_after_what_its_parts_share(pool):
    assert merged("na10,na11", pool)[0].name == "na1"
    assert merged("na11,na21", pool)[0].name == "na"
    assert merged(" na10 , na11 ", pool)[0].name == "na1"


def test_a_name_that_matches_nothing_returns_none(pool):
    assert merged("zzz9", pool) is None
    assert merged("na10,zzz9", pool)[1] == ["na10"]
