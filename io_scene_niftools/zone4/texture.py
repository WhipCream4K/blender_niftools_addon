"""Zone4-specific texture helpers."""

import os

import bpy
import numpy as np
import io_scene_niftools
from nifgen.formats.nif import classes as NifClasses

from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.modules.nif_export.property.texture import TextureWriter
from io_scene_niftools.utils.logging import NifLog
from io_scene_niftools.utils.singleton import NifData, NifOp


def _resolve_toonramp_source_path():
    addon_dir = os.path.dirname(os.path.abspath(io_scene_niftools.__file__))
    candidates = [
        os.path.join(addon_dir, "dependencies", "bin", "ToonRamp.png"),
        os.path.join(os.path.dirname(addon_dir), "bin", "ToonRamp.png")
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _rgb24_from_image(img):
    width, height = img.size
    pixels = img.pixels[:]
    if len(pixels) < width * height * 4:
        raise ValueError("Image pixel buffer is incomplete")

    pitch = ((width * 3 + 3) // 4) * 4
    rows = []
    for y in range(height):
        row = bytearray(width * 3)
        for x in range(width):
            idx = (y * width + x) * 4
            r = min(255, max(0, int(round(pixels[idx] * 255.0))))
            g = min(255, max(0, int(round(pixels[idx + 1] * 255.0))))
            b = min(255, max(0, int(round(pixels[idx + 2] * 255.0))))
            base = x * 3
            row[base:base + 3] = bytes((r, g, b))
        if pitch > width * 3:
            row.extend(b"\x00" * (pitch - width * 3))
        rows.append(bytes(row))
    return b"".join(rows), pitch


def _build_nipixeldata_from_rgb24(payload, width, height, pitch):
    pix = NifClasses.NiPixelData(NifData.data)

    try:
        pix.pixel_format = NifClasses.PixelFormat.FMT_RGB
    except Exception:
        pix.pixel_format = 'FMT_RGB'

    try:
        pix.tiling = NifClasses.PixelTiling.TILE_NONE
    except Exception:
        pix.tiling = 'TILE_NONE'

    try:
        pix.bytes_per_pixel = 3
    except Exception:
        pass

    try:
        pix.bits_per_pixel = 24
    except Exception:
        pass

    if hasattr(NifData, 'data') and hasattr(NifData.data, 'version') and NifData.data.version <= 168034305:
        pix.red_mask = 0x000000FF
        pix.green_mask = 0x0000FF00
        pix.blue_mask = 0x00FF0000
        pix.alpha_mask = 0

    if hasattr(pix, "old_fast_compare"):
        pix.old_fast_compare[:] = [96, 8, -126, 0, 0, 8, 16, 0]

    try:
        pix.num_mipmaps = 1
    except Exception:
        pass
    try:
        pix.reset_field('mipmaps')
        m = pix.mipmaps[0]
        m.width = width
        m.height = height
        m.offset = 0
        m.num_pixels = len(payload)
    except Exception:
        pass

    arr = np.frombuffer(payload, dtype=np.uint8)
    try:
        pix.num_pixels = len(arr)
    except Exception:
        pass

    try:
        if hasattr(pix, 'num_faces') and getattr(pix, 'num_faces', 1) > 1:
            expected_len = pix.num_pixels * pix.num_faces
        else:
            expected_len = pix.num_pixels
        if len(arr) != expected_len:
            if hasattr(pix, 'num_faces') and getattr(pix, 'num_faces', 1) > 1:
                pix.num_pixels = len(arr) // max(1, pix.num_faces)
            else:
                pix.num_pixels = len(arr)
        if hasattr(NifData, 'data') and hasattr(NifData.data, 'version'):
            if NifData.data.version >= 168034306 and hasattr(pix, 'num_faces') and getattr(pix, 'num_faces', 1) > 1:
                arr = arr.reshape((pix.num_pixels * pix.num_faces,))
            else:
                arr = arr.reshape((pix.num_pixels,))
        else:
            arr = arr.reshape((pix.num_pixels,))
        try:
            pix.pixel_data = arr
        except Exception:
            pix.data = arr
    except Exception as ex:
        NifLog.warn(f"Failed to assign ToonRamp pixel data: {ex}")

    return pix


def _build_toonramp_source(toonramp_src):
    embed = getattr(NifOp.props, 'embed_textures', False)

    srctex = NifClasses.NiSourceTexture(NifData.data)
    srctex.use_external = not embed
    srctex.file_name = "ToonRamp.dds"

    if bpy.context.scene.niftools_scene.nif_version >= 0x0A000100:
        srctex.format_prefs.pixel_layout = 6
    elif bpy.context.scene.niftools_scene.game == 'ZONE4':
        srctex.format_prefs.pixel_layout = 6
    else:
        srctex.format_prefs.pixel_layout = 5
    srctex.format_prefs.use_mipmaps = 1
    srctex.format_prefs.alpha_format = 3
    srctex.is_static = 1

    source_path = toonramp_src if os.path.exists(toonramp_src) else None
    source_key = TextureWriter._build_source_texture_key(srctex, source_path=source_path, target_fourcc='RGB24')
    existing = TextureWriter._source_texture_key_map.get(source_key)
    if existing:
        return existing

    if embed and source_path:
        try:
            abs_source = bpy.path.abspath(source_path)
            img = None
            for cand in bpy.data.images:
                cand_path = bpy.path.abspath(getattr(cand, "filepath", ""))
                if cand_path and os.path.normcase(cand_path) == os.path.normcase(abs_source):
                    img = cand
                    break
                if os.path.basename(getattr(cand, "filepath", "")) == os.path.basename(abs_source):
                    img = cand
                    break
                if cand.name == os.path.basename(abs_source):
                    img = cand
                    break

            loaded_here = False
            if img is None:
                img = bpy.data.images.load(abs_source, check_existing=True)
                loaded_here = True

            if not img.has_data or img.size[0] == 0 or img.size[1] == 0:
                img.reload()

            # Access pixels to force loading
            _ = img.pixels[:4] if img.size[0] and img.size[1] else None

            if not img.has_data or img.size[0] == 0 or img.size[1] == 0:
                raise ValueError(f"Image '{os.path.basename(abs_source)}' has no pixel data")

            rgb_payload, rgb_pitch = _rgb24_from_image(img)
            pix = _build_nipixeldata_from_rgb24(rgb_payload, img.size[0], img.size[1], rgb_pitch)

            try:
                srctex.pixel_data = pix
            except Exception:
                srctex.data = pix
            srctex.use_external = False

            NifLog.info(f"Zone4 ToonRamp embedded from Blender pixels: {img.size[0]}x{img.size[1]}")

            if loaded_here:
                bpy.data.images.remove(img)
        except Exception as ex:
            srctex.use_external = True
            NifLog.warn(f"Failed to embed ToonRamp from Blender image: {ex}. Falling back to external reference.")
    elif embed:
        srctex.use_external = True
        NifLog.warn(f"ToonRamp.png not found at '{toonramp_src}'. Falling back to external reference.")

    if hasattr(srctex, 'name') and not getattr(srctex, 'name', None):
        srctex.name = os.path.basename(srctex.file_name)

    block = block_store.register_block(srctex)
    TextureWriter._register_source_texture_key(block, source_key)
    return block


def apply_toonramp_shader_texture(texprop):
    """Append a ToonRamp shader texture to the texturing property."""
    toonramp_src = _resolve_toonramp_source_path()
    toonramp_source = _build_toonramp_source(toonramp_src)

    shader_desc = NifClasses.ShaderTexDesc(NifData.data)
    shader_desc.has_map = True
    shader_desc.map_id = 0
    shader_desc.map.source = toonramp_source
    shader_desc.map.uv_set = 0

    texprop.shader_textures.append(shader_desc)
    texprop.num_shader_textures = len(texprop.shader_textures)

    NifLog.info("Zone4 ToonRamp shader texture appended")
