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

from io_scene_niftools.file_io.nif import NifFile as KFFile
from io_scene_niftools.modules.nif_import.animation.transform import TransformAnimation
from io_scene_niftools.nif_common import NifCommon
from io_scene_niftools.utils import math
from io_scene_niftools.utils.singleton import NifOp
from io_scene_niftools.utils.logging import NifLog, NifError


class KfImport(NifCommon):

    def __init__(self, operator, context):
        NifCommon.__init__(self, operator, context)

        # Helper systems
        self.transform_anim = TransformAnimation()

    def execute(self):
        """Main import function."""

        try:
            dirname = os.path.dirname(NifOp.props.filepath)
            kf_files = [os.path.join(dirname, file.name) for file in NifOp.props.files if file.name.lower().endswith(".kf")]
            # if an armature is present, prepare the bones for all actions
            b_armature = math.get_armature()
            if b_armature:
                # the axes used for bone correction depend on the armature in our scene
                math.set_bone_orientation(b_armature.data.niftools.axis_forward, b_armature.data.niftools.axis_up)
                # get nif space bind pose of armature here for all anims
                self.transform_anim.get_bind_data(b_armature)
            for kf_file in kf_files:
                kfdata = KFFile.load_nif(kf_file)

                # Log all blocks in the imported KF file for debugging
                NifLog.info(f"========== IMPORT KF FILE: {os.path.basename(kf_file)} ==========")
                self.log_kf_blocks(kfdata)
                NifLog.info("========== END IMPORT KF BLOCKS ==========")

                self.apply_scale(kfdata, NifOp.props.scale_correction)

                # calculate and set frames per second
                self.transform_anim.set_frames_per_second(kfdata.roots)
                for kf_root in kfdata.roots:
                    self.transform_anim.import_kf_root(kf_root, b_armature)

        except NifError:
            return {'CANCELLED'}

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
