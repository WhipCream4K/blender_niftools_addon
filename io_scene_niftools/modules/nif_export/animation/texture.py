"""This script contains classes to help export texture animations."""

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
from nifgen.formats.nif import classes as NifClasses

import io_scene_niftools.utils.logging
from io_scene_niftools.modules.nif_export.animation import Animation
from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.modules.nif_export.property.texture.writer import TextureWriter


class TextureAnimation(Animation):

    def __init__(self):
        super().__init__()

    def export_flip_controller(self, fliptxt, texture, target, target_tex):
        # TODO [animation] port code to use native Blender image strip system
        #                  despite its name a NiFlipController does not flip / mirror a texture
        #                  instead it swaps through a list of textures for a sprite animation
        #
        # fliptxt is a blender text object containing the n_flip definitions
        # texture is the texture object in blender ( texture is used to checked for pack and mipmap flags )
        # target is the NiTexturingProperty
        # target_tex is the texture to n_flip ( 0 = base texture, 4 = glow texture )
        #
        # returns exported NiFlipController

        tlist = fliptxt.asLines()

        # create a NiFlipController
        n_flip = block_store.create_block("NiFlipController", fliptxt)
        target.add_controller(n_flip)

        # fill in NiFlipController's values
        n_flip.flags = 8  # active
        n_flip.frequency = 1.0
        start = bpy.context.scene.frame_start

        n_flip.start_time = (start - 1) * self.fps
        n_flip.stop_time = (bpy.context.scene.frame_end - start) * self.fps
        n_flip.texture_slot = target_tex

        count = 0
        for t in tlist:
            if len(t) == 0:
                continue  # skip empty lines
            # create a NiSourceTexture for each n_flip
            tex = TextureWriter.export_source_texture(texture, t)
            n_flip.num_sources += 1
            n_flip.sources.append(tex)
            count += 1
        if count < 2:
            raise io_scene_niftools.utils.logging.NifError(f"Error in Texture Flip buffer '{fliptxt.name}': must define at least two textures")
        n_flip.delta = (n_flip.stop_time - n_flip.start_time) / count

    def export_texture_transform_controller(self, b_mat, mapping_node, texprop, texdesc, slot_name):
        if not b_mat or not mapping_node or not texprop or not texdesc:
            return False

        node_tree = b_mat.node_tree
        if not node_tree or not node_tree.animation_data or not node_tree.animation_data.action:
            return False

        tex_slot_map = {
            "Base": NifClasses.TexType.BASE_MAP,
            "Dark": NifClasses.TexType.DARK_MAP,
            "Detail": NifClasses.TexType.DETAIL_MAP,
            "Gloss": NifClasses.TexType.GLOSS_MAP,
            "Glow": NifClasses.TexType.GLOW_MAP,
            "Bump Map": NifClasses.TexType.BUMP_MAP,
            "Decal 0": NifClasses.TexType.DECAL_0_MAP,
            "Decal 1": NifClasses.TexType.DECAL_1_MAP,
            "Decal 2": NifClasses.TexType.DECAL_2_MAP,
        }
        tex_slot = tex_slot_map.get(slot_name)
        if tex_slot is None:
            return False

        fcurves = node_tree.animation_data.action.fcurves
        if not fcurves:
            return False

        data_targets = (
            (NifClasses.TransformMember.TT_TRANSLATE_U, 1, 0, 1.0),
            (NifClasses.TransformMember.TT_TRANSLATE_V, 1, 1, -1.0),
            (NifClasses.TransformMember.TT_ROTATE, 2, 2, 1.0),
            (NifClasses.TransformMember.TT_SCALE_U, 3, 0, 1.0),
            (NifClasses.TransformMember.TT_SCALE_V, 3, 1, 1.0),
        )

        has_keys = False
        for operation, input_index, array_index, multiplier in data_targets:
            data_path = f'nodes["{mapping_node.name}"].inputs[{input_index}].default_value'
            fcurve = next((fcu for fcu in fcurves if fcu.data_path == data_path and fcu.array_index == array_index), None)
            if not fcurve or not fcurve.keyframe_points:
                continue
            has_keys = True

            n_key_data = block_store.create_block("NiFloatData", fcurve)
            n_key_data.data.num_keys = len(fcurve.keyframe_points)
            n_key_data.data.interpolation = NifClasses.KeyType.LINEAR_KEY
            n_key_data.data.reset_field("keys")

            for i, n_key in enumerate(n_key_data.data.keys):
                frame = fcurve.keyframe_points[i].co[0]
                value = fcurve.keyframe_points[i].co[1] * multiplier
                n_key.arg = n_key_data.data.interpolation
                n_key.time = frame / self.fps
                n_key.value = value

            n_ctrl = block_store.create_block("NiTextureTransformController", fcurve)
            n_ipol = block_store.create_block("NiFloatInterpolator", fcurve)
            n_ctrl.interpolator = n_ipol
            n_ctrl.shader_map = False
            n_ctrl.texture_slot = tex_slot
            n_ctrl.operation = operation
            n_ctrl.data = n_key_data
            n_ipol.data = n_key_data
            self.set_flags_and_timing(n_ctrl, [fcurve])
            texprop.add_controller(n_ctrl)

        if not has_keys:
            return False

        if hasattr(texdesc, "has_texture_transform"):
            texdesc.has_texture_transform = True
        if hasattr(texdesc, "transform_method"):
            texdesc.transform_method = NifClasses.TransformMethod.MAX
        if hasattr(texdesc, "center"):
            texdesc.center.u = 0.5
            texdesc.center.v = 0.5
        if hasattr(texdesc, "translation"):
            try:
                loc = mapping_node.inputs[1].default_value
                texdesc.translation.u = loc[0]
                texdesc.translation.v = -loc[1]
            except (TypeError, IndexError):
                pass
        if hasattr(texdesc, "scale"):
            try:
                scale = mapping_node.inputs[3].default_value
                texdesc.scale.u = scale[0]
                texdesc.scale.v = scale[1]
            except (TypeError, IndexError):
                pass
        if hasattr(texdesc, "rotation"):
            try:
                rotation = mapping_node.inputs[2].default_value
                texdesc.rotation = rotation[2]
            except (TypeError, IndexError):
                pass
        return True
