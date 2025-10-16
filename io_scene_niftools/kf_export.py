"""This script imports Netimmerse/Gamebryo nif files to Blender."""

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

import os
import bpy

from io_scene_niftools.modules.nif_export.animation.transform import TransformAnimation
from io_scene_niftools.nif_common import NifCommon
from io_scene_niftools.utils import math
from io_scene_niftools.utils.singleton import NifOp, NifData
from io_scene_niftools.utils.logging import NifLog, NifError
from io_scene_niftools.modules.nif_export import scene


class KfExport(NifCommon):

    def __init__(self, operator, context):
        NifCommon.__init__(self, operator, context)

        # Helper systems
        self.transform_anim = TransformAnimation()

    def execute(self):
        """Main export function."""

        NifLog.info(f"Exporting {NifOp.props.filepath}")

        # extract directory, base name, extension
        directory = os.path.dirname(NifOp.props.filepath)
        filebase, fileext = os.path.splitext(os.path.basename(NifOp.props.filepath))

        if bpy.context.scene.niftools_scene.game == 'UNKNOWN':
            raise NifError("You have not selected a game. Please select a game in the scene tab.")

        prefix = "x" if bpy.context.scene.niftools_scene.game in ('MORROWIND',) else ""
        self.version, data = scene.get_version_data()
        # todo[anim] - change to KfData, but create_controller() [and maybe more] has to be updated first
        NifData.init(data)

        b_armature = math.get_armature()
        # some scenes may not have an armature, so nothing to do here
        if b_armature:
            math.set_bone_orientation(b_armature.data.niftools.axis_forward, b_armature.data.niftools.axis_up)

        NifLog.info("Creating keyframe tree")
        kf_root = self.transform_anim.export_kf_root(b_armature)

        # write kf (and xkf if asked)
        ext = ".kf"
        NifLog.info(f"Writing {prefix}{ext} file")

        data.roots = [kf_root]
        data.neosteam = (bpy.context.scene.niftools_scene.game == 'NEOSTEAM')

        # scale correction for the skeleton
        self.apply_scale(data, 1 / NifOp.props.scale_correction)

        data.validate()

        # Log all blocks in the exported KF file for debugging
        NifLog.info(f"========== EXPORT KF FILE: {prefix + filebase + ext} ==========")
        self.log_kf_blocks(data)
        NifLog.info("========== END EXPORT KF BLOCKS ==========")

        kffile = os.path.join(directory, prefix + filebase + ext)
        with open(kffile, "wb") as stream:
            data.write(stream)

        NifLog.info("Finished successfully")
        return {'FINISHED'}

    def log_kf_blocks(self, kfdata):
        """Log all blocks in the KF file for debugging purposes."""
        NifLog.info(f"KF File Version: {kfdata.version}")
        NifLog.info(f"Number of roots: {len(kfdata.roots)}")
        
        for idx, root in enumerate(kfdata.roots):
            NifLog.info(f"\nRoot Block {idx}: {type(root).__name__} - Name: '{root.name}'")
            self._log_block_tree(root, indent=1)
    
    def _log_block_tree(self, block, indent=0, visited=None):
        """Recursively log block tree structure."""
        if visited is None:
            visited = set()
        
        # Avoid infinite loops from circular references
        block_id = id(block)
        if block_id in visited:
            return
        visited.add(block_id)
        
        prefix = "  " * indent
        block_type = type(block).__name__
        
        # Log basic block info
        block_name = getattr(block, 'name', 'N/A')
        NifLog.info(f"{prefix}├─ {block_type}: '{block_name}'")
        
        # Log important attributes based on block type
        if hasattr(block, 'num_controlled_blocks'):
            NifLog.info(f"{prefix}│  └─ num_controlled_blocks: {block.num_controlled_blocks}")
        
        if hasattr(block, 'controlled_blocks'):
            for cb_idx, cb in enumerate(block.controlled_blocks):
                target_name = getattr(cb, 'target_name', 'N/A')
                node_name = getattr(cb, 'node_name', 'N/A') if hasattr(cb, 'node_name') else 'N/A'
                NifLog.info(f"{prefix}│  └─ ControlledBlock[{cb_idx}]: target='{target_name}', node='{node_name}'")
                
                # Log interpolator info
                if hasattr(cb, 'interpolator') and cb.interpolator:
                    interp = cb.interpolator
                    interp_type = type(interp).__name__
                    NifLog.info(f"{prefix}│     └─ Interpolator: {interp_type}")
                    
                    # Log keyframe data if present
                    if hasattr(interp, 'data') and interp.data:
                        kfd = interp.data
                        kfd_type = type(kfd).__name__
                        NifLog.info(f"{prefix}│        └─ Data: {kfd_type}")
                        
                        if hasattr(kfd, 'num_rotation_keys'):
                            NifLog.info(f"{prefix}│           ├─ rotation_keys: {kfd.num_rotation_keys}")
                        if hasattr(kfd, 'translations') and hasattr(kfd.translations, 'num_keys'):
                            NifLog.info(f"{prefix}│           ├─ translation_keys: {kfd.translations.num_keys}")
                        if hasattr(kfd, 'scales') and hasattr(kfd.scales, 'num_keys'):
                            NifLog.info(f"{prefix}│           └─ scale_keys: {kfd.scales.num_keys}")
        
        # Log text keys if present
        if hasattr(block, 'text_keys') and block.text_keys:
            text_keys = block.text_keys
            if hasattr(text_keys, 'num_text_keys'):
                NifLog.info(f"{prefix}│  └─ TextKeys: {text_keys.num_text_keys} keys")
                if hasattr(text_keys, 'text_keys'):
                    for tk_idx, tk in enumerate(text_keys.text_keys[:5]):  # Show first 5
                        NifLog.info(f"{prefix}│     └─ [{tk_idx}] time={tk.time:.3f}, value='{tk.value}'")
                    if text_keys.num_text_keys > 5:
                        NifLog.info(f"{prefix}│     └─ ... and {text_keys.num_text_keys - 5} more")
        
        # Log timing info
        if hasattr(block, 'start_time'):
            NifLog.info(f"{prefix}│  ├─ start_time: {block.start_time}")
        if hasattr(block, 'stop_time'):
            NifLog.info(f"{prefix}│  ├─ stop_time: {block.stop_time}")
        if hasattr(block, 'frequency'):
            NifLog.info(f"{prefix}│  ├─ frequency: {block.frequency}")
        if hasattr(block, 'cycle_type'):
            NifLog.info(f"{prefix}│  └─ cycle_type: {block.cycle_type}")

