"""Clip scale keys size what hangs off a joint — no game files needed.

Every race wields the same weapon mesh; the client sizes it by the scale each race's
clips key on the grip joint. These pin that the scale survives posing, re-parenting
onto a hand, and skinning.
"""

import pytest

from xi.entity.anim.xi_export import (
    AnimationSection,
    AnimationTrack,
    Joint,
    JointRef,
    VertexSource,
    apply_parent_overrides,
    compute_global_transforms,
    pose_joints_at_playback_frame,
    resolve_corner_vertex,
)

IDENTITY = (0.0, 0.0, 0.0, 1.0)


def joint(index, parent, translation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    return Joint(index=index, parent_index=parent, rotation=IDENTITY,
                 translation=translation, scale=scale)


def vertex_on(joint_index, p0):
    ref = JointRef(index=joint_index, flipped_index=joint_index, flip_axis=0)
    return VertexSource(joint_ref0=ref, joint_ref1=ref, joint_index0=joint_index,
                        joint_index1=0, mirrored_joint_index0=joint_index,
                        mirrored_joint_index1=0, p0=p0, p1=(0.0, 0.0, 0.0),
                        n0=(0.0, 0.0, 1.0), n1=(0.0, 0.0, 0.0), weight0=1.0, weight1=0.0)


def test_posing_carries_the_clip_scale():
    track = AnimationTrack(joint_index=1, rotations=[IDENTITY], translations=[(0.0, 0.0, 0.0)],
                           scales=[(0.7, 0.7, 0.7)])
    clip = AnimationSection(name="btl0", num_joints=2, num_frames=1, keyframe_duration=1.0,
                            tracks={1: track})
    posed = pose_joints_at_playback_frame([joint(0, -1), joint(1, 0)], clip, 0)
    assert posed[0].scale == (1.0, 1.0, 1.0)
    assert posed[1].scale == pytest.approx((0.7, 0.7, 0.7))


def test_scale_shortens_child_offsets_and_accumulates():
    joints = [joint(0, -1), joint(1, 0, scale=(0.5, 0.5, 0.5)),
              joint(2, 1, translation=(0.0, 0.0, 2.0), scale=(0.5, 0.5, 0.5))]
    g = compute_global_transforms(joints)
    assert g[2].translation == pytest.approx((0.0, 0.0, 1.0))
    assert g[2].scale == pytest.approx((0.25, 0.25, 0.25))


def test_grip_keeps_its_scale_when_it_adopts_the_hand():
    hand = joint(1, 0, translation=(1.0, 0.0, 0.0))
    grip = joint(2, 0, translation=(5.0, 5.0, 5.0), scale=(0.7, 0.7, 0.7))
    joints = apply_parent_overrides([joint(0, -1), hand, grip], {2: 1})
    g = compute_global_transforms(joints)
    assert g[2].translation == pytest.approx((1.0, 0.0, 0.0))
    assert g[2].scale == pytest.approx((0.7, 0.7, 0.7))
    # The bending-only path agrees with the rewritten hierarchy.
    bent = compute_global_transforms([joint(0, -1), hand, grip], parent_overrides={2: 1})
    assert bent[2].scale == pytest.approx((0.7, 0.7, 0.7))


def test_skinned_vertices_are_scaled_about_their_joint():
    joints = [joint(0, -1), joint(1, 0, translation=(0.0, 1.0, 0.0), scale=(0.5, 0.5, 0.5))]
    g = compute_global_transforms(joints)
    position, normal, _, _ = resolve_corner_vertex(vertex_on(1, (0.0, 0.0, 2.0)), g, False)
    assert position == pytest.approx((0.0, 1.0, 1.0))
    assert normal == pytest.approx((0.0, 0.0, 1.0))
