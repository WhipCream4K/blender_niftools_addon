"""This script contains classes to help export blender bone or object level transform(ation) animations into NIF controllers."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2019, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****

import bpy
import mathutils

from nifgen.formats.nif import classes as NifClasses

from io_scene_niftools.modules.nif_export.animation import Animation
from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.utils import math, consts
from io_scene_niftools.utils.logging import NifError, NifLog
from io_scene_niftools.utils.consts import QUAT, EULER, LOC, SCALE
from io_scene_niftools.utils.singleton import NifData


class TransformAnimation(Animation):

    def __init__(self):
        super().__init__()

    @staticmethod
    def iter_frame_key(fcurves, mathutilclass):
        """
        Iterator that yields a tuple of frame and key for all fcurves.
        Assumes the fcurves are sampled at the same time and all have the same amount of keys
        Return the key in the desired MathutilsClass
        """
        for point in zip(*[fcu.keyframe_points for fcu in fcurves]):
            frame = point[0].co[0]
            key = [k.co[1] for k in point]
            yield frame, mathutilclass(key)

    def export_kf_root(self, b_armature=None):
        """Creates and returns a KF root block and exports controllers for objects and bones"""
        scene = bpy.context.scene
        nif_scene = scene.niftools_scene
        game = nif_scene.game
        if game in ('MORROWIND', 'FREEDOM_FORCE'):
            kf_root = block_store.create_block("NiSequenceStreamHelper")
        elif nif_scene.is_bs() or game in (
                'CIVILIZATION_IV', 'ZOO_TYCOON_2', 'FREEDOM_FORCE_VS_THE_3RD_REICH',
                'SHIN_MEGAMI_TENSEI_IMAGINE', 'SID_MEIER_S_PIRATES', 'ZONE4'):
            kf_root = block_store.create_block("NiControllerSequence")
        else:
            raise NifError(f"Keyframe export for '{game}' is not supported.")

        anim_textextra = self.create_text_keys(kf_root)

        targetname = "Scene Root"

        # If no armature was explicitly provided, try to auto-detect one in the scene
        if not b_armature:
            for obj in bpy.data.objects:
                if getattr(obj, 'type', None) == 'ARMATURE':
                    b_armature = obj
                    NifLog.info(f"Auto-detected armature '{b_armature.name}' for KF export")
                    break

        # Pre-seed string palette for ZONE4 to control ordering before any controllers add strings
        if game == 'ZONE4' and isinstance(kf_root, NifClasses.NiControllerSequence):
            if not kf_root.string_palette:
                kf_root.string_palette = NifClasses.NiStringPalette(NifData.data)
            palette = kf_root.string_palette.palette
            # Reference order: 'Bip01 Position' first, then controller type, then bone names, then the two root entries
            palette.add_string("Bip01 Position")
            palette.add_string("NiTransformController")
            # If we already know the armature, add bone names now. If not, they will be appended when we detect it below.
            if b_armature:
                for bone in b_armature.data.bones:
                    palette.add_string(bone.name)
            # Always add root markers at the end of the palette seeding
            palette.add_string("Bip01 Base")
            palette.add_string("Bip01 Base NonAccum")

        # per-node animation
        if b_armature:
            b_action = self.get_active_action(b_armature)

            # # If no active action, attempt to pull the first action from NLA tracks
            # if not b_action and getattr(b_armature, 'animation_data', None):
            #     nla = b_armature.animation_data.nla_tracks
            #     for track in nla:
            #         for strip in getattr(track, 'strips', []):
            #             if strip and getattr(strip, 'action', None) and strip.action.fcurves:
            #                 b_action = strip.action
            #                 NifLog.info(f"Using NLA action '{b_action.name}' for armature '{b_armature.name}'")
            #                 break
            #         if b_action:
            #             break
            # if not b_action:
            #     NifLog.info(f"Armature '{b_armature.name}' has no active action and no NLA action with fcurves; bone export will be skipped.")

            for b_bone in b_armature.data.bones:
                self.export_transforms(kf_root, b_armature, b_action, b_bone)
            
            # For ZONE4, ensure critical nodes exist even without animation
            # These nodes are searched for by AnimationCompressor.h FindInterpolator() function:
            # - "Bip01" (line 576) - CRITICAL, causes error if missing
            # - "Bip01 Position" (line 611) - Used for forward movement/rotation
            if game == 'ZONE4' and isinstance(kf_root, NifClasses.NiControllerSequence):
                required_nodes = ["Bip01 Position", "Bip01"]
                for node_name in required_nodes:
                    # Check if this bone exists in armature
                    if node_name in b_armature.data.bones:
                        # Check if it was already exported (has fcurves)
                        bone_path_prefix = f"pose.bones[\"{node_name}\"]"
                        has_fcurves = any(fcu for fcu in (b_action.fcurves if b_action else [])
                                        if fcu and isinstance(fcu.data_path, str) and fcu.data_path.startswith(bone_path_prefix))
                        
                        # If no fcurves, create a controller with identity transform
                        if not has_fcurves:
                            NifLog.info(f"Adding required ZONE4 node without animation: {node_name}")
                            n_kfc, n_kfi = self.create_controller(kf_root, node_name, 26)
                            if n_kfi:
                                # Set identity transform
                                n_kfi.transform.translation.x = 0.0
                                n_kfi.transform.translation.y = 0.0
                                n_kfi.transform.translation.z = 0.0
                                n_kfi.transform.rotation.w = 1.0
                                n_kfi.transform.rotation.x = 0.0
                                n_kfi.transform.rotation.y = 0.0
                                n_kfi.transform.rotation.z = 0.0
                                n_kfi.transform.scale = 1.0
                
            if nif_scene.is_skyrim():
                targetname = "NPC Root [Root]"
            else:
                # quick hack to set correct target name
                if game == 'ZONE4':
                    targetname = "Bip01 Base"
                elif "Bip01" in b_armature.data.bones:
                    targetname = "Bip01"
                elif "Bip02" in b_armature.data.bones:
                    targetname = "Bip02"


        # per-object animation
        else:
            for b_obj in bpy.data.objects:
                b_action = self.get_active_action(b_obj)
                self.export_transforms(kf_root, b_obj, b_action)

        self.export_text_keys(b_action, anim_textextra)

        kf_root.name = b_action.name
        kf_root.unknown_int_1 = 1
        kf_root.weight = 1.0
        
        # Restore cycle_type from import if available, otherwise default to CLAMP
        if "nif_cycle_type" in b_action:
            kf_root.cycle_type = NifClasses.CycleType(b_action["nif_cycle_type"])
            NifLog.info(f"Restored cycle_type from import: {kf_root.cycle_type}")
        else:
            # New animation created in Blender, default to CLAMP
            kf_root.cycle_type = NifClasses.CycleType.CYCLE_CLAMP
            NifLog.info("New animation, using default cycle_type: CYCLE_CLAMP")
        
        kf_root.frequency = 1.0
        if game in ('SID_MEIER_S_PIRATES', 'ZONE4'):
            kf_root.accum_root_name = targetname

        if anim_textextra.num_text_keys > 0:
            kf_root.start_time = anim_textextra.text_keys[0].time
            kf_root.stop_time = anim_textextra.text_keys[anim_textextra.num_text_keys - 1].time
        else:
            kf_root.start_time = scene.frame_start / self.fps
            kf_root.stop_time = scene.frame_end / self.fps

        kf_root.target_name = targetname
        return kf_root

    def export_transforms(self, parent_block, b_obj, b_action, bone=None):
        """
        If bone == None, object level animation is exported.
        If a bone is given, skeletal animation is exported.
        """

        # If there's no action, skip exporting transforms (pose-only workaround removed)
        if not b_action:
            return

        # blender object must exist
        assert b_obj
        # if a bone is given, b_obj must be an armature
        if bone:
            assert type(b_obj.data) == bpy.types.Armature

        # just for more detailed error reporting later on
        bonestr = ""

        # skeletal animation - with bone correction & coordinate corrections
        if bone:
            # get bind matrix for bone
            bind_matrix = math.get_object_bind(bone)
            # Prefer collecting fcurves by explicit data_path to avoid relying on group presence
            bone_path_prefix = f"pose.bones[\"{bone.name}\"]"
            exp_fcurves = [
                fcu for fcu in b_action.fcurves
                if fcu and isinstance(fcu.data_path, str) and fcu.data_path.startswith(bone_path_prefix)
            ]
            # If nothing collected via data_path, fall back to action groups if available
            if not exp_fcurves and bone.name in b_action.groups:
                exp_fcurves = list(b_action.groups[bone.name].channels)
            # just for more detailed error reporting later on
            bonestr = f" in bone {bone.name}"
            target_name = block_store.get_full_name(bone)
            priority = bone.niftools.priority
            # If still no fcurves for this bone, skip it (bind pose keys should have been created during import)
            if not exp_fcurves:
                return

        # object level animation - no coordinate corrections
        elif not bone:

            # raise error on any objects parented to bones
            if b_obj.parent and b_obj.parent_type == "BONE":
                raise NifError(
                    f"{b_obj.name} is parented to a bone AND has animations. The nif format does not support this!")

            target_name = block_store.get_full_name(b_obj)
            priority = 0

            # we have either a root object (Scene Root), in which case we take the coordinates without modification
            # or a generic object parented to an empty = node
            # objects may have an offset from their parent that is not apparent in the user input (ie. UI values and keyframes)
            # we want to export matrix_local, and the keyframes are in matrix_basis, so do:
            # matrix_local = matrix_parent_inverse * matrix_basis
            bind_matrix = b_obj.matrix_parent_inverse
            exp_fcurves = [fcu for fcu in b_action.fcurves if
                       fcu.data_path in (QUAT, EULER, LOC, SCALE)]
            if not exp_fcurves:
                return

        else:
            # bone isn't keyframed in this action, nothing to do here
            return

        # decompose the bind matrix
        bind_scale, bind_rot, bind_trans = math.decompose_srt(bind_matrix)
        n_kfc, n_kfi = self.create_controller(parent_block, target_name, priority)

        # If no controller was created (e.g., GEOM_NIF mode), skip animation export
        if not n_kfc:
            return

        # fill in the non-trivial values
        start_frame, stop_frame = b_action.frame_range
        self.set_flags_and_timing(n_kfc, exp_fcurves, start_frame, stop_frame)

        # get the desired fcurves for each data type from exp_fcurves
        quaternions = [fcu for fcu in exp_fcurves if fcu.data_path.endswith("quaternion")]
        translations = [fcu for fcu in exp_fcurves if fcu.data_path.endswith("location")]
        eulers = [fcu for fcu in exp_fcurves if fcu.data_path.endswith("euler")]
        scales = [fcu for fcu in exp_fcurves if fcu.data_path.endswith("scale")]
        # quiet: internal counts only

        # ensure that those groups that are present have all their fcurves
        for fcus, num_fcus in ((quaternions, 4), (eulers, 3), (translations, 3), (scales, 3)):
            if fcus and len(fcus) != num_fcus:
                raise NifError(
                    f"Incomplete key set {bonestr} for action {b_action.name}."
                    f"Ensure that if a bone is keyframed for a property, all channels are keyframed.")

        # go over all fcurves collected above and transform and store all their keys
        quat_curve = []
        euler_curve = []
        trans_curve = []
        scale_curve = []
        # For euler-driven rotations, also compute quaternions to avoid gimbal lock
        quat_from_euler_curve = []
        # Determine rotation order from Blender if using eulers
        euler_order = 'XYZ'
        try:
            if bone:
                rot_mode = b_obj.pose.bones[bone.name].rotation_mode
            else:
                rot_mode = b_obj.rotation_mode
            if rot_mode in {'XYZ','XZY','YXZ','YZX','ZXY','ZYX'}:
                euler_order = rot_mode
        except Exception:
            pass
        for frame, quat in self.iter_frame_key(quaternions, mathutils.Quaternion):
            quat = math.export_keymat(bind_rot, quat.to_matrix().to_4x4(), bone).to_quaternion()
            quat_curve.append((frame, quat))

        for frame, euler in self.iter_frame_key(eulers, mathutils.Euler):
            # Build matrix from incoming euler using its order, then convert with bind/space fix
            euler_mat = euler.to_matrix().to_4x4()
            keymat = math.export_keymat(bind_rot, euler_mat, bone)
            # Re-express as euler in the detected order (for completeness)
            eul = keymat.to_euler(euler_order, euler)
            euler_curve.append((frame, eul))
            # Also compute quaternion to avoid gimbal issues
            q = keymat.to_quaternion()
            quat_from_euler_curve.append((frame, q))

        for frame, trans in self.iter_frame_key(translations, mathutils.Vector):
            keymat = math.export_keymat(bind_rot, mathutils.Matrix.Translation(trans), bone)
            trans = keymat.to_translation() + bind_trans
            trans_curve.append((frame, trans))

        for frame, scale in self.iter_frame_key(scales, mathutils.Vector):
            # just use the first scale curve and assume even scale over all curves
            scale_curve.append((frame, scale[0]))

        if n_kfi:
            # set the default transforms of the interpolator as the bone's bind pose
            n_kfi.transform.translation.x, n_kfi.transform.translation.y, n_kfi.transform.translation.z = bind_trans
            n_kfi.transform.rotation.w, n_kfi.transform.rotation.x, n_kfi.transform.rotation.y, n_kfi.transform.rotation.z = bind_rot.to_quaternion()
            n_kfi.transform.scale = bind_scale

            if max(len(c) for c in (quat_curve, euler_curve, trans_curve, scale_curve)) > 0:
                # number of frames is > 0, so add transform data
                n_kfd = block_store.create_block("NiTransformData", exp_fcurves)
                n_kfi.data = n_kfd
            else:
                # no need to add any keys, done
                return

        else:
            # add the keyframe data
            n_kfd = block_store.create_block("NiKeyframeData", exp_fcurves)
            n_kfc.data = n_kfd
            NifLog.info(f"Using NiKeyframeData for '{target_name}' (old NIF version)")

        # TODO [animation] support other interpolation modes, get interpolation from blender?
        #                  probably requires additional data like tangents and stuff

        # finally we can export the data calculated above
        # Special-case: ZONE4 requires quaternion LINKEY (compressor only accepts NiRotKey::LINKEY).
        force_pcm_quat_lin = (bpy.context.scene.niftools_scene.game == 'ZONE4')

        if force_pcm_quat_lin:
            # Choose a quaternion curve: prefer authored quats, else derive from eulers
            use_quats = quat_curve if quat_curve else quat_from_euler_curve
            # If still nothing, leave NOINTERP (handled later by zero keys)
            if use_quats:
                # continuity fix
                fixed_quats = []
                prev = None
                for frame, q in use_quats:
                    if prev is not None and (prev.w*q.w + prev.x*q.x + prev.y*q.y + prev.z*q.z) < 0.0:
                        q = mathutils.Quaternion((-q.w, -q.x, -q.y, -q.z))
                    fixed_quats.append((frame, q))
                    prev = q
                # sort and deduplicate by frame, ensure strictly increasing times
                fixed_quats.sort(key=lambda it: it[0])
                dedup_quats = []
                last_t = None
                for t, q in fixed_quats:
                    if last_t is None or t > last_t:
                        dedup_quats.append((t, q))
                        last_t = t
                    else:
                        # bump time slightly to maintain monotonicity
                        last_t = last_t + 1e-6
                        dedup_quats.append((last_t, q))
                use_quats = dedup_quats
                n_kfd.rotation_type = NifClasses.KeyType.LINEAR_KEY
                n_kfd.num_rotation_keys = len(use_quats)
                n_kfd.reset_field("quaternion_keys")
                for key, (frame, quat) in zip(n_kfd.quaternion_keys, use_quats):
                    key.time = frame / self.fps
                    key.value.w = quat.w
                    key.value.x = quat.x
                    key.value.y = quat.y
                    key.value.z = quat.z
        else:
            # Prefer quaternion rotation tracks to avoid gimbal lock; if no explicit quaternion fcurves,
            # but we have euler keys, use quaternions derived from those eulers.
            # Ensure quaternion continuity (avoid sudden flips) by keeping dot(prev, curr) >= 0.
            if not quat_curve and quat_from_euler_curve:
                quat_curve = quat_from_euler_curve

            if quat_curve:
                # continuity fix
                fixed_quats = []
                prev = None
                for frame, q in quat_curve:
                    if prev is not None and (prev.w*q.w + prev.x*q.x + prev.y*q.y + prev.z*q.z) < 0.0:
                        q = mathutils.Quaternion((-q.w, -q.x, -q.y, -q.z))
                    fixed_quats.append((frame, q))
                    prev = q
                # sort and deduplicate by frame, ensure strictly increasing times
                fixed_quats.sort(key=lambda it: it[0])
                dedup_quats = []
                last_t = None
                for t, q in fixed_quats:
                    if last_t is None or t > last_t:
                        dedup_quats.append((t, q))
                        last_t = t
                    else:
                        last_t = last_t + 1e-6
                        dedup_quats.append((last_t, q))
                quat_curve = dedup_quats
                n_kfd.rotation_type = NifClasses.KeyType.QUADRATIC_KEY
                n_kfd.num_rotation_keys = len(quat_curve)
                n_kfd.reset_field("quaternion_keys")
                for key, (frame, quat) in zip(n_kfd.quaternion_keys, quat_curve):
                    key.time = frame / self.fps
                    key.value.w = quat.w
                    key.value.x = quat.x
                    key.value.y = quat.y
                    key.value.z = quat.z
            elif euler_curve:
                # Fallback: write XYZ axes keys if no quaternion data is available
                n_kfd.rotation_type = NifClasses.KeyType.XYZ_ROTATION_KEY
                n_kfd.num_rotation_keys = 1  # do not set to frame count per historical exporter behavior
                n_kfd.reset_field("xyz_rotations")
                for i, coord in enumerate(n_kfd.xyz_rotations):
                    coord.num_keys = len(euler_curve)
                    coord.interpolation = NifClasses.KeyType.LINEAR_KEY
                    coord.reset_field("keys")
                    for key, (frame, euler) in zip(coord.keys, euler_curve):
                        key.time = frame / self.fps
                        key.value = euler[i]
        # quiet: rotation keys summary suppressed

        n_kfd.translations.interpolation = NifClasses.KeyType.LINEAR_KEY
        n_kfd.translations.num_keys = len(trans_curve)
        n_kfd.translations.reset_field("keys")
        for key, (frame, trans) in zip(n_kfd.translations.keys, trans_curve):
            key.time = frame / self.fps
            key.value.x, key.value.y, key.value.z = trans
        # quiet

        n_kfd.scales.interpolation = NifClasses.KeyType.LINEAR_KEY
        n_kfd.scales.num_keys = len(scale_curve)
        n_kfd.scales.reset_field("keys")
        for key, (frame, scale) in zip(n_kfd.scales.keys, scale_curve):
            key.time = frame / self.fps
            key.value = scale
        # quiet

    def create_text_keys(self, kf_root):
        """Create the text keys before filling in the data so that the extra data hierarchy is correct"""
        # add a NiTextKeyExtraData block
        n_text_extra = block_store.create_block("NiTextKeyExtraData", None)
        if isinstance(kf_root, NifClasses.NiControllerSequence):
            kf_root.text_keys = n_text_extra
        elif isinstance(kf_root, NifClasses.NiSequenceStreamHelper):
            kf_root.add_extra_data(n_text_extra)
        return n_text_extra

    def export_text_keys(self, b_action, n_text_extra):
        """Process b_action's pose markers and populate the extra string data block."""
        NifLog.info("Exporting animation groups")
        self.add_dummy_markers(b_action)
        # create a text key for each frame descriptor
        n_text_extra.num_text_keys = len(b_action.pose_markers)
        n_text_extra.reset_field("text_keys")
        f0, f1 = b_action.frame_range
        for key, marker in zip(n_text_extra.text_keys, b_action.pose_markers):
            f = marker.frame
            if (f < f0) or (f > f1):
                NifLog.warn(f"Marker out of animated range ({f} not between [{f0}, {f1}])")
            key.time = f / self.fps
            key.value = marker.name.replace('/', '\r\n')

    def add_dummy_controllers(self):
        NifLog.info("Adding controllers and interpolators for skeleton")
        # note: block_store.block_to_obj changes during iteration, so need list copy
        for n_block in list(block_store.block_to_obj.keys()):
            if isinstance(n_block, NifClasses.NiNode) and n_block.name == "Bip01":
                for n_bone in n_block.tree(block_type=NifClasses.NiNode):
                    n_kfc, n_kfi = self.transform_anim.create_controller(n_bone, n_bone.name)
                    # todo [anim] use self.nif_export.animationhelper.set_flags_and_timing
                    n_kfc.flags = 12
                    n_kfc.frequency = 1.0
                    n_kfc.phase = 0.0
                    n_kfc.start_time = consts.FLOAT_MAX
                    n_kfc.stop_time = consts.FLOAT_MIN
