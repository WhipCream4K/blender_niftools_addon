""" Nif User Interface, custom nif properties for materials"""

# ***** BEGIN LICENSE BLOCK *****
# 
# Copyright © 2014, NIF File Format Library and Tools contributors.
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
from bpy.props import (PointerProperty,
                       FloatVectorProperty,
                       IntProperty,
                       BoolProperty,
                       FloatProperty,
                       EnumProperty,
                       )
from bpy.types import PropertyGroup

from io_scene_niftools.utils.decorators import register_classes, unregister_classes


class TextureNodeProperty(PropertyGroup):
    """Adds custom properties to image texture nodes"""

    pixel_format: EnumProperty(
        name='Pixel Format',
        description='Pixel format for embedding this texture',
        items=[
            ('AUTO', 'Auto', 'Auto-select DXT1 (no alpha) or DXT5 (alpha). Use for most textures.'),
            ('FMT_RGB', 'FMT_RGB', '24-bit RGB source. Exports as R8G8B8A8_UNORM. Use for uncompressed color without alpha.'),
            ('FMT_RGBA', 'FMT_RGBA', '32-bit RGBA source. Exports as R8G8B8A8_UNORM. Use for uncompressed color with alpha.'),
            ('FMT_PAL', 'FMT_PAL', '8-bit palette indices. Exports as R8_UNORM. Use only for indexed textures.'),
            ('FMT_PALA', 'FMT_PALA', '8-bit palette + alpha. Exports as R8G8_UNORM. Use only for indexed+alpha textures.'),
            ('FMT_DXT1', 'FMT_DXT1', 'DXT1 compressed. Use for opaque textures.'),
            ('FMT_DXT3', 'FMT_DXT3', 'DXT3 compressed. Use for sharp alpha edges.'),
            ('FMT_DXT5', 'FMT_DXT5', 'DXT5 compressed. Use for smooth alpha.'),
            ('FMT_RGB24NONINT', 'FMT_RGB24NONINT', 'Legacy 24-bit PS2 format. Exports as R8G8B8A8_UNORM. Use only for legacy assets.'),
            ('FMT_BUMP', 'FMT_BUMP', 'dU/dV bump map. Exports as BC5_UNORM. Use for normal-style maps.'),
            ('FMT_BUMPLUMA', 'FMT_BUMPLUMA', 'Bump + luma. Exports as BC5_UNORM. Use if a tool expects bump+luma.'),
            ('FMT_RENDERSPEC', 'FMT_RENDERSPEC', 'Renderer-specific. Exports as BC7_UNORM. Use for high-quality general textures.'),
            ('FMT_1CH', 'FMT_1CH', 'Single channel. Exports as R8_UNORM. Use for masks or grayscale.'),
            ('FMT_2CH', 'FMT_2CH', 'Two channel. Exports as R8G8_UNORM. Use for XY vectors or paired masks.'),
            ('FMT_3CH', 'FMT_3CH', 'Three channel. Exports as R8G8B8A8_UNORM. Use for RGB data (alpha unused).'),
            ('FMT_4CH', 'FMT_4CH', 'Four channel. Exports as R8G8B8A8_UNORM. Use for RGBA data.'),
            ('FMT_DEPTH_STENCIL', 'FMT_DEPTH_STENCIL', 'Depth/stencil surface. Falls back to AUTO. Use only if required by pipeline.'),
            ('FMT_UNKNOWN', 'FMT_UNKNOWN', 'Unknown/unspecified. Falls back to AUTO. Prefer AUTO instead.'),
        ],
        default='AUTO'
    )


class Material(PropertyGroup):
    """Adds custom properties to material"""

    ambient_preview: BoolProperty(
        name='Ambient Preview', description='Allows a viewport preview of the ambient property', default=False)

    ambient_color: FloatVectorProperty(
        name='Ambient', subtype='COLOR', default=[1.0, 1.0, 1.0], min=0.0, max=1.0)

    emissive_preview: BoolProperty(
        name='Emissive Preview', description='Allows a viewport preview of the emissive property', default=False)

    emissive_color: FloatVectorProperty(
        name='Emissive', subtype='COLOR', default=[0.0, 0.0, 0.0], min=0.0, max=1.0)

    emissive_alpha: FloatVectorProperty(
        name='Alpha', subtype='COLOR', default=[0.0, 0.0, 0.0], min=0.0, max=1.0)

    lightingeffect1: FloatProperty(
        name='Lighting Effect 1',
        default=0.3
    )
    lightingeffect2: FloatProperty(
        name='Lighting Effect 2',
        default=2
    )


class AlphaFlags(PropertyGroup):
    """Adds custom properties to material"""

    alphaflag: IntProperty(
        name='Alpha Flag',
        default=0
    )

    textureflag: IntProperty(
        name='Texture Flag',
        default=0
    )

    materialflag: IntProperty(
        name='Material Flag',
        default=0
    )


CLASSES = [
    TextureNodeProperty,
    Material,
    AlphaFlags
]


def register():
    register_classes(CLASSES, __name__)

    bpy.types.Material.niftools = bpy.props.PointerProperty(type=Material)
    bpy.types.Material.niftools_alpha = bpy.props.PointerProperty(type=AlphaFlags)
    bpy.types.ShaderNodeTexImage.niftools = bpy.props.PointerProperty(type=TextureNodeProperty)


def unregister():
    del bpy.types.Material.niftools
    del bpy.types.Material.niftools_alpha
    del bpy.types.ShaderNodeTexImage.niftools

    unregister_classes(CLASSES, __name__)
