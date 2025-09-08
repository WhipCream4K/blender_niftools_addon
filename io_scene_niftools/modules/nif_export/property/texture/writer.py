"""This script contains helper methods to export textures sources."""

# ***** BEGIN LICENSE BLOCK *****
# 
# Copyright © 2013, NIF File Format Library and Tools contributors.
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

import os.path
import struct
import numpy as np

import bpy
from nifgen.formats.nif import classes as NifClasses

import io_scene_niftools.utils.logging
from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.utils import math
from io_scene_niftools.utils.singleton import NifOp
from io_scene_niftools.utils.logging import NifLog
from io_scene_niftools.utils.singleton import NifData


class TextureWriter:

    @staticmethod
    def export_source_texture(n_texture=None, filename=None):
        """Export a NiSourceTexture.

        :param n_texture: The n_texture object in blender to be exported.
        :param filename: The full or relative path to the n_texture file
            (this argument is used when exporting NiFlipControllers
            and when exporting default shader slots that have no use in
            being imported into Blender).
        :return: The exported NiSourceTexture block.
        """

        # create NiSourceTexture
        srctex = NifClasses.NiSourceTexture(NifData.data)
        # Determine external vs embedded based on export option
        embed = getattr(NifOp.props, 'embed_textures', False)
        srctex.use_external = not embed
        if filename is not None:
            # preset filename
            srctex.file_name = filename
        elif n_texture is not None:
            # Keep filename even when embedding; engines typically ignore it when use_external=False,
            # but tools may display it and some pipelines expect a name hint.
            srctex.file_name = TextureWriter.export_texture_filename(n_texture)
        else:
            # this probably should not happen
            NifLog.warn("Exporting source texture without texture or filename (bug?).")

        # fill in default values (TODO: can we use 6 for everything?)
        if bpy.context.scene.niftools_scene.nif_version >= 0x0A000100:
            srctex.pixel_layout = 6
        else:
            srctex.pixel_layout = 5
        srctex.use_mipmaps = 1
        srctex.alpha_format = 3
        srctex.unknown_byte = 1

        # if embedding requested, try to embed DDS as NiPixelData (DXT1 only for now)
        if embed:
            try:
                # Log Blender node/image diagnostics to help resolve format/path
                if n_texture is not None and isinstance(n_texture, bpy.types.ShaderNodeTexImage):
                    img = getattr(n_texture, 'image', None)
                    if img is None:
                        NifLog.warn(f"Image Texture node '{n_texture.name}' has no image assigned.")
                    else:
                        try:
                            cs = getattr(getattr(img, 'colorspace_settings', None), 'name', None)
                            NifLog.info(
                                f"Image diagnostics for node '{n_texture.name}':\n"
                                f"  filepath      = '{getattr(img, 'filepath', '')}'\n"
                                f"  filepath_raw  = '{getattr(img, 'filepath_raw', '')}'\n"
                                f"  size          = {getattr(img, 'size', [0,0])[0]}x{getattr(img, 'size', [0,0])[1]}\n"
                                f"  file_format   = '{getattr(img, 'file_format', '')}'\n"
                                f"  packed        = {'yes' if getattr(img, 'packed_file', None) else 'no'}\n"
                                f"  colorspace    = '{cs}'"
                            )
                        except Exception:
                            pass
                # Resolve path from provided filename or texture node
                def resolve_dds_path(n_texture_local, filename_local):
                    candidates = []
                    # 1) direct parameter
                    if filename_local:
                        candidates.append(filename_local)
                    # 2) from node image paths (raw, resolved, and .dds variant)
                    if n_texture_local is not None and isinstance(n_texture_local, bpy.types.ShaderNodeTexImage) and n_texture_local.image:
                        img = n_texture_local.image
                        for p in (getattr(img, 'filepath', None), getattr(img, 'filepath_raw', None)):
                            if p:
                                candidates.append(p)
                                # add .dds variant
                                if p.lower().endswith(('.png', '.tga', '.bmp', '.jpg', '.jpeg')):
                                    candidates.append(p[:-4] + '.dds')
                        # 3) exporter’s sanitized name (may be basename)
                        try:
                            candidates.append(TextureWriter.export_texture_filename(n_texture_local))
                        except Exception:
                            pass
                    # 4) if a basename, try relative to current .blend folder
                    more = []
                    try:
                        blend_dir = bpy.path.abspath('//')
                        for c in candidates:
                            if c and (not os.path.isabs(c)):
                                more.append(os.path.join(blend_dir, c))
                    except Exception:
                        pass
                    candidates.extend(more)
                    # Deduplicate while preserving order
                    seen = set()
                    uniq = []
                    for c in candidates:
                        if c and c not in seen:
                            uniq.append(c)
                            seen.add(c)
                    # Log candidates
                    for c in uniq:
                        NifLog.debug(f"Embed resolve candidate: '{c}' -> '{bpy.path.abspath(c)}'")
                    # Return first existing .dds
                    for c in uniq:
                        absc = bpy.path.abspath(c)
                        if absc.lower().endswith('.dds') and os.path.exists(absc):
                            return absc
                    return None

                tex_path = resolve_dds_path(n_texture, filename)
                if tex_path:
                    NifLog.info(f"Embedding DDS from '{tex_path}'")
                    with open(bpy.path.abspath(tex_path), 'rb') as f:
                        data = f.read()
                    # Minimal DDS parser for DXT1
                    # DDS header: magic (4) + header (124)
                    if data[:4] != b'DDS ':
                        raise ValueError('Not a DDS file')
                    header = data[4:128]
                    # DWORD sizes are little-endian
                    # Offsets per Microsoft DDS spec
                    dwSize, dwFlags, dwHeight, dwWidth, dwPitchOrLinearSize, dwDepth, dwMipMapCount = struct.unpack('<7I', header[0:28])
                    pf = header[76:108]  # DDS_PIXELFORMAT (32 bytes)
                    # Correct layout: size (I), flags (I), fourCC (4s), RGBBitCount (I), RMask (I), GMask (I), BMask (I), AMask (I)
                    (pfSize, pfFlags, pfFourCC, pfRGBBitCount, pfRMask, pfGMask, pfBMask, pfAMask) = struct.unpack('<II4sI4I', pf)
                    fourcc = pfFourCC.decode('ascii', errors='ignore').strip('\x00')
                    # Map FourCC to format and bytes-per-4x4-block
                    fourcc_to_fmt = {
                        'DXT1': ('FMT_DXT1', 8),
                        'DXT3': ('FMT_DXT3', 16),
                        'DXT5': ('FMT_DXT5', 16),
                    }
                    # Handle DX10 extended header mapping to BC1/2/3 (DXT1/3/5)
                    payload_offset = 128
                    if fourcc == 'DX10':
                        # DDS_HEADER_DXT10 is 20 bytes after the main header
                        if len(data) < 128 + 20:
                            raise ValueError('DX10 header truncated')
                        (dxgi_format, resource_dim, misc_flag, array_size, misc_flags2) = struct.unpack('<5I', data[128:148])
                        payload_offset = 148
                        # DXGI_FORMAT_BC1_UNORM = 71, BC1_UNORM_SRGB = 72
                        # DXGI_FORMAT_BC2_UNORM = 74, BC2_UNORM_SRGB = 75
                        # DXGI_FORMAT_BC3_UNORM = 77, BC3_UNORM_SRGB = 78
                        if dxgi_format in (71, 72):
                            fourcc = 'DXT1'
                        elif dxgi_format in (74, 75):
                            fourcc = 'DXT3'
                        elif dxgi_format in (77, 78):
                            fourcc = 'DXT5'
                        else:
                            raise ValueError(f'Only BC1/BC2/BC3 embedding supported (DXGI format {dxgi_format})')
                    NifLog.debug(f"DDS parsed: fourcc='{fourcc}', width={dwWidth}, height={dwHeight}")
                    if fourcc not in fourcc_to_fmt:
                        # Attempt auto-convert to DXT1 if enabled
                        if getattr(NifOp.props, 'auto_convert_to_dxt1', False):
                            # Build texconv command
                            import tempfile, subprocess, shutil
                            src = bpy.path.abspath(tex_path)
                            workdir = tempfile.mkdtemp(prefix='nif_embed_')
                            out = os.path.join(workdir, os.path.basename(src))
                            # Replace extension with .dds (texconv decides)
                            out_dds = out
                            # Resolve texconv path in priority order:
                            # 1) user-specified path in export operator
                            # 2) bundled binary under addon folder: io_scene_niftools/bin/texconv.exe (Windows)
                            # 3) system PATH
                            user_texconv = getattr(NifOp.props, 'texconv_path', '')
                            if user_texconv:
                                texconv = user_texconv
                            else:
                                # try bundled location using the addon package root
                                try:
                                    import io_scene_niftools as _nif_addon_pkg
                                    addon_dir = os.path.dirname(os.path.abspath(_nif_addon_pkg.__file__))
                                except Exception:
                                    # fallback: older heuristic
                                    addon_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                                # Preferred location only: io_scene_niftools/dependencies/bin/texconv.exe
                                bundled_new = os.path.join(addon_dir, 'dependencies', 'bin', 'texconv.exe')
                                NifLog.info(f"texconv resolution: addon_dir='{addon_dir}'")
                                NifLog.info(f"texconv candidate (new)='{bundled_new}' exists={os.path.exists(bundled_new)}")
                                if os.path.exists(bundled_new):
                                    texconv = bundled_new
                                    NifLog.info(f"Using bundled texconv at '{texconv}'")
                                else:
                                    # Extra diagnostics: list directory if present
                                    try:
                                        dep_dir = os.path.dirname(bundled_new)
                                        if os.path.isdir(dep_dir):
                                            NifLog.info(f"contents of '{dep_dir}': {os.listdir(dep_dir)}")
                                    except Exception:
                                        pass
                                    texconv = 'texconv'
                            cmd = [texconv, '-nologo', '-f', 'DXT1', '-o', workdir, src]
                            NifLog.info(f"Auto-converting '{src}' to DXT1 via: {' '.join(cmd)}")
                            try:
                                subprocess.run(cmd, check=True, capture_output=True)
                                # texconv writes to workdir with same basename; find produced dds
                                produced = None
                                base = os.path.splitext(os.path.basename(src))[0]
                                for cand in os.listdir(workdir):
                                    if cand.lower().startswith(base.lower()) and cand.lower().endswith('.dds'):
                                        produced = os.path.join(workdir, cand)
                                        break
                                if not produced:
                                    raise RuntimeError('texconv did not produce a DDS file')
                                with open(produced, 'rb') as f2:
                                    data = f2.read()
                                header = data[4:128]
                                dwSize, dwFlags, dwHeight, dwWidth, dwPitchOrLinearSize, dwDepth, dwMipMapCount = struct.unpack('<7I', header[0:28])
                                pf = header[76:108]
                                (pfSize, pfFlags, pfFourCC, pfRGBBitCount, pfRMask, pfGMask, pfBMask, pfAMask) = struct.unpack('<II4sI4I', pf)
                                fourcc = pfFourCC.decode('ascii', errors='ignore').strip('\x00')
                                payload_offset = 128
                                # Handle DX10 extended header
                                if fourcc == 'DX10':
                                    if len(data) < 148:
                                        raise ValueError('DX10 header truncated after auto-convert')
                                    (dxgi_format, resource_dim, misc_flag, array_size, misc_flags2) = struct.unpack('<5I', data[128:148])
                                    payload_offset = 148
                                    if dxgi_format in (71, 72):
                                        fourcc = 'DXT1'
                                    elif dxgi_format in (74, 75):
                                        fourcc = 'DXT3'
                                    elif dxgi_format in (77, 78):
                                        fourcc = 'DXT5'
                                    else:
                                        raise ValueError(f"Auto-convert produced unsupported DXGI format '{dxgi_format}'")
                                # Some texconv builds may leave pfFourCC empty despite -f DXT1; trust requested format
                                if not fourcc:
                                    fourcc = 'DXT1'
                                NifLog.info(f"Auto-convert succeeded. New DDS fourcc='{fourcc}', size={dwWidth}x{dwHeight}")
                                if fourcc not in fourcc_to_fmt:
                                    raise ValueError(f"Auto-convert produced unsupported format '{fourcc}'")
                            except Exception as conv_ex:
                                NifLog.warn(f"Auto-convert to DXT1 failed: {conv_ex}")
                                raise ValueError(f'Only DXT1/DXT3/DXT5 embedding supported for now (found {fourcc})')
                        else:
                            raise ValueError(f'Only DXT1/DXT3/DXT5 embedding supported for now (found {fourcc})')
                    # Determine mip count
                    mip_count = dwMipMapCount if (dwFlags & 0x20000) and dwMipMapCount > 0 else 1
                    if getattr(NifOp.props, 'embed_only_base_mipmap', True):
                        mip_count_to_write = 1
                    else:
                        mip_count_to_write = mip_count
                    # Calculate offsets and gather payloads
                    payload = data[payload_offset:]
                    w, h = dwWidth, dwHeight
                    offset = 0
                    mip_entries = []
                    chunks = []
                    bytes_per_block = fourcc_to_fmt[fourcc][1]
                    for i in range(mip_count_to_write):
                        bw = max(1, (w + 3) // 4)
                        bh = max(1, (h + 3) // 4)
                        size = bw * bh * bytes_per_block
                        chunks.append(payload[offset:offset + size])
                        mip_entries.append((w, h, offset, size))  # store byte size for this mip
                        offset += size
                        w = max(1, w // 2)
                        h = max(1, h // 2)
                    # Build NiPixelData
                    pix = NifClasses.NiPixelData(NifData.data)
                    # Set simple fields with safe guards
                    try:
                        fmt_name = fourcc_to_fmt[fourcc][0]
                        pix.pixel_format = getattr(NifClasses.PixelFormat, fmt_name)
                    except Exception:
                        # fallback for enum set by name if needed
                        try:
                            pix.pixel_format = fmt_name
                        except Exception:
                            pass
                    try:
                        pix.tiling = NifClasses.PixelTiling.TILE_NONE
                    except Exception:
                        try:
                            pix.tiling = 'TILE_NONE'
                        except Exception:
                            pass
                    try:
                        pix.num_mipmaps = len(mip_entries)
                    except Exception:
                        pass
                    # Assign mipmaps list if present
                    try:
                        pix.reset_field('mipmaps')
                        for n, (mw, mh, mo, npix) in enumerate(mip_entries):
                            m = pix.mipmaps[n]
                            m.width = mw
                            m.height = mh
                            m.offset = mo
                            m.num_pixels = npix
                    except Exception:
                        pass
                    # Assign pixel_data as numpy uint8 array
                    concatenated = b''.join(chunks)
                    arr = np.frombuffer(concatenated, dtype=np.uint8)
                    try:
                        pix.pixel_data = arr
                    except Exception:
                        # Alternate field name in some schemas
                        try:
                            pix.data = arr
                        except Exception:
                            raise
                    # Link to source texture
                    try:
                        srctex.pixel_data = pix
                    except Exception:
                        # Alternate attribute name
                        try:
                            srctex.data = pix
                        except Exception:
                            raise
                else:
                    NifLog.warn("Embed Textures enabled but a readable DDS file could not be resolved from material node or filename; falling back to external reference.")
                    srctex.use_external = True
            except Exception as ex:
                NifLog.warn(f"Failed to embed texture as NiPixelData (DXT1): {ex}. Falling back to external reference.")
                srctex.use_external = True

        # search for duplicate
        for block in block_store.block_to_obj:
            if isinstance(block, NifClasses.NiSourceTexture) and block.get_hash() == srctex.get_hash():
                return block

        # no identical source texture found, so use and register the new one
        return block_store.register_block(srctex, n_texture)

    def export_tex_desc(self, texdesc=None, uv_set=0, b_texture_node=None):
        """Helper function for export_texturing_property to export each texture slot."""
        texdesc.uv_set = uv_set
        texdesc.source = TextureWriter.export_source_texture(b_texture_node)

    @staticmethod
    def export_texture_filename(b_texture_node):
        """Returns image file name from b_texture_node.

        @param b_texture_node: The b_texture_node object in blender.
        @return: The file name of the image used in the b_texture_node.
        """

        if not isinstance(b_texture_node, bpy.types.ShaderNodeTexImage):
            raise io_scene_niftools.utils.logging.NifError(f"Expected a Shader node texture, got {type(b_texture_node)}")
        # get filename from image

        # TODO [b_texture_node] still needed? can b_texture_node.image be None in current blender?
        # check that image is loaded
        if b_texture_node.image is None:
            raise io_scene_niftools.utils.logging.NifError(f"Image type texture has no file loaded ('{b_texture_node.name}')")

        filename = b_texture_node.image.filepath

        # warn if packed flag is enabled
        if b_texture_node.image.packed_file:
            NifLog.warn(f"Packed image in texture '{b_texture_node.name}' ignored, exporting as '{filename}' instead.")

        # try and find a DDS alternative, force it if required
        ddsfilename = f"{(filename[:-4])}.dds"
        if os.path.exists(bpy.path.abspath(ddsfilename)) or NifOp.props.force_dds:
            filename = ddsfilename

        # sanitize file path
        nif_scene = bpy.context.scene.niftools_scene
        if not (nif_scene.is_bs() or nif_scene.game in ('MORROWIND',)):
            # strip b_texture_node file path
            filename = os.path.basename(filename)

        else:
            # strip the data files prefix from the b_texture_node's file name
            filename = filename.lower()
            idx = filename.find("textures")
            if idx >= 0:
                filename = filename[idx:]
            elif not os.path.exists(bpy.path.abspath(filename)):
                pass
            else:
                NifLog.warn(f"{filename} does not reside in a 'Textures' folder; texture path will be stripped and textures may not display in-game")
                filename = os.path.basename(filename)
        # for linux export: fix path separators
        return filename.replace('/', '\\')

