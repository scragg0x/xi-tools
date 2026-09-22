"""Per-weapon engaged-motion lookup — needs a game install (FFXI_DIR)."""

import struct

import pytest

from xi.entity.anim.xi_motion_tables import battle_motion_spec
from xi.gear.xi_pose import _load, parse_info, sources_from_look
from xi.gear.xi_stance import (
    BATTLE_CLIP,
    FALLBACK_BATTLE_CLIP,
    IDLE_CLIP,
    STANCES,
    battle_clip_sources,
    stance_clips,
)

pytestmark = pytest.mark.usefixtures("root")

# HumeMale model ids: a one-handed sword, a great sword, a staff, a bow, a shield.
SWORD, GREAT_SWORD, STAFF, BOW, SHIELD = 185, 319, 342, 98, 48


def look(**weapons) -> bytes:
    """A bare HumeMale wearing nothing but the named weapons."""
    order = ["head", "body", "hands", "legs", "feet", "main", "sub", "ranged"]
    values = []
    for index, slot in enumerate(order, start=1):
        model = weapons.get(slot)
        if model is None and index > 5:
            values.append(0)  # an empty hand carries no model at all
        else:
            values.append((index << 12) | (model or 0))  # armour 0 = the bare mesh
    return struct.pack("<HBB8H", 1, 1, 1, *values)


def anim_type(model_id: int, slot: str = "main") -> int | None:
    sources, _skel, _race = sources_from_look(look(**{slot: model_id}))
    source = next(s for s in sources if s.slot == slot)
    return parse_info(_load(source).data, source.sections)["weapon_animation_type"]


def test_a_weapon_names_the_animation_type_the_client_reads():
    assert anim_type(SWORD) is not None
    # Ranged weapons declare none — a bow has no melee stance of its own.
    assert anim_type(BOW, "ranged") is None


def test_one_and_two_handed_weapons_resolve_to_different_packs():
    sword = battle_motion_spec("HumeMale", anim_type(SWORD))
    great = battle_motion_spec("HumeMale", anim_type(GREAT_SWORD))
    staff = battle_motion_spec("HumeMale", anim_type(STAFF))
    assert sword and great and staff
    # The two-handed grips come from the pack, so they must not share the sword's.
    assert len({sword, great, staff}) == 3


def test_each_race_has_its_own_pack_for_the_same_weapon():
    hume = battle_motion_spec("HumeMale", anim_type(SWORD))
    galka = battle_motion_spec("Galka", anim_type(SWORD))
    assert hume and galka and hume != galka


def test_clip_sources_pick_the_main_hand_and_fall_back_sensibly():
    sources, _skel, race = sources_from_look(look(main=GREAT_SWORD))
    clips = battle_clip_sources(sources, race)
    assert [c.slot for c in clips] == ["motion"]
    assert clips[0].path.exists()

    # Bare hands still square up: a character with no weapon fights with fists.
    bare, _s, race = sources_from_look(look())
    assert battle_clip_sources(bare, race)

    # A bow gets nothing — no engaged clip poses an arm around one, so the caller's
    # generic guard holds it better than a fists-up stance would.
    ranged, _s, race = sources_from_look(look(ranged=BOW))
    assert battle_clip_sources(ranged, race) == []


def test_battle_draws_what_neutral_stows():
    sources, _skel, race = sources_from_look(look(main=SWORD, sub=SHIELD))
    battle = stance_clips(sources, race, "battle")
    neutral = stance_clips(sources, race, "neutral")

    assert battle["draw_melee"] and battle["anim"] == BATTLE_CLIP
    assert battle["clip_sources"]  # the sword's own motion pack
    assert not neutral["draw_melee"] and neutral["anim"] == IDLE_CLIP
    assert neutral["clip_sources"]  # the race's idle companions
    # Neither hands a shield-and-sword character a bow it is not carrying.
    assert not battle["draw_ranged"] and not neutral["draw_ranged"]


def test_a_bow_alone_is_held_in_both_stances():
    # A stowed ranged weapon is not rendered at all, so the alternative to holding it
    # is a set whose only weapon is invisible.
    sources, _skel, race = sources_from_look(look(ranged=BOW))
    for stance in STANCES:
        assert stance_clips(sources, race, stance)["draw_ranged"]
    assert stance_clips(sources, race, "battle")["anim"] == FALLBACK_BATTLE_CLIP

