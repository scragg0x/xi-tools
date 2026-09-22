"""Stand an assembled character the way the client does — ``battle`` or ``neutral``.

:func:`stance_clips` reads what a worn set carries and returns the keyword arguments
for :func:`xi.gear.xi_pose.build_pose` that pose it in a stance. Nothing needs to be
said about dual wield, shields or two-handers: the client picks the clips from the
weapons, and so does this.

* **battle** — weapons drawn, posed from ``btl`` in the main weapon's own motion pack
  (race battle base + the weapon's ``weaponAnimationType``). That pack is what puts a
  great sword in two hands and a staff across the body. Bare hands square up with fists.
* **neutral** — weapons stowed, posed from the race idle with its companion packs, which
  carry each weapon's grip joint to where it is worn: sword on the hip, shield and
  two-hander on the back.

A stowed ranged weapon is not rendered at all (see :mod:`xi.gear.xi_pose`), so a set
whose only weapon is ranged holds it in both stances rather than showing nothing.

Every lookup degrades instead of failing: a pack this install cannot resolve leaves
``clip_sources`` empty and the pose falls back to the clips the body DAT carries.

    from xi.gear.xi_pose import build_pose, sources_from_look
    from xi.gear.xi_stance import stance_clips

    sources, skeleton, race = sources_from_look(look)
    build_pose(sources, out_dir, skeleton_dat=skeleton, **stance_clips(sources, race, "battle"))
"""

from typing import List, Optional

from xi.entity.anim.xi_motion_tables import battle_motion_spec, movement_motion_specs
from xi.gear.xi_pose import WEAPON_SLOTS, PoseSource, _load, _resolve_dat, parse_info

STANCES = ("neutral", "battle")

# Digit-less, so every rig variant in the supplied packs merges into one full-body pose.
BATTLE_CLIP = "btl"
IDLE_CLIP = "idl"
# For a set with no pack to take a stance from (a ranged weapon alone): the race's
# generic guard. Both rig variants are named — na10 carries the legs, na11 the arms.
FALLBACK_BATTLE_CLIP = "na10,na11"
# The client's weaponAnimationType for bare hands.
UNARMED_ANIMATION_TYPE = 2


def stance_clips(sources: List[PoseSource], race: str, stance: str = "battle") -> dict:
    """``build_pose`` keyword arguments (``clip_sources``, ``anim``, ``draw_melee``,
    ``draw_ranged``) that stand ``sources`` in ``stance`` — one of :data:`STANCES`."""
    if stance not in STANCES:
        raise ValueError(f"unknown stance {stance!r}; one of {', '.join(STANCES)}")
    if stance == "neutral":
        return {"clip_sources": neutral_clip_sources(race), "anim": IDLE_CLIP,
                "draw_melee": False, "draw_ranged": _ranged_only(sources)}
    clips = battle_clip_sources(sources, race)
    return {"clip_sources": clips, "anim": BATTLE_CLIP if clips else FALLBACK_BATTLE_CLIP,
            "draw_melee": True, "draw_ranged": _ranged_only(sources)}


def neutral_clip_sources(race: str) -> List[PoseSource]:
    """The race's movement companion packs, so ``idl`` poses the arms and the stowed
    weapons as well as the legs. ``[]`` when this install cannot resolve them."""
    try:
        specs = movement_motion_specs(race)
    except (OSError, ValueError):
        return []
    return [s for s in (_motion_source(spec) for spec in specs) if s]


def battle_clip_sources(sources: List[PoseSource], race: str) -> List[PoseSource]:
    """The motion pack holding the engaged ``btl`` stance for what ``sources`` wield.

    The main hand decides, then the offhand; a set with no typed weapon uses the
    unarmed pack. ``[]`` when the only weapon is ranged (bows and guns declare no type,
    and no engaged clip poses an arm around one) or no pack resolves on this install."""
    for anim_type in _stance_animation_types(sources):
        try:
            spec = battle_motion_spec(race, anim_type)
        except (OSError, ValueError):
            continue
        source = _motion_source(spec) if spec else None
        if source:
            return [source]
    return []


def _stance_animation_types(sources: List[PoseSource]) -> List[int]:
    """Weapon animation types to try, best first."""
    types: List[int] = []
    for slot in WEAPON_SLOTS:
        source = next((s for s in sources if s.slot == slot), None)
        if source is None:
            continue
        try:
            anim_type = _weapon_animation_type(source)
        except (OSError, ValueError):
            continue
        if anim_type is not None and anim_type not in types:
            types.append(anim_type)
    if not types and not _ranged_only(sources):
        types.append(UNARMED_ANIMATION_TYPE)
    return types


def _weapon_animation_type(source: PoseSource) -> Optional[int]:
    # Read a copy: build_pose loads its sources itself, and the caller's stay untouched.
    loaded = source if source.data else _load(PoseSource(path=source.path, slot=source.slot))
    return parse_info(loaded.data, loaded.sections)["weapon_animation_type"]


def _motion_source(spec: str) -> Optional[PoseSource]:
    try:
        return PoseSource(path=_resolve_dat(spec), slot="motion")
    except FileNotFoundError:
        return None


def _ranged_only(sources: List[PoseSource]) -> bool:
    """Whether a ranged weapon is the only weapon this set carries."""
    return {s.slot for s in sources} & set(WEAPON_SLOTS) == {"ranged"}
