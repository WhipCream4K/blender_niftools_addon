# Setup script for compiling Python modules to C extensions using Cython
# This allows you to distribute compiled .pyd (Windows) or .so (Linux/Mac) files
# instead of readable .py source files

from setuptools import setup, Extension
from Cython.Build import cythonize
import os
import sys

# Define which modules you want to compile
# Compiling ALL modules except:
# - io_scene_niftools/__init__.py (Blender needs to read bl_info dict)
# - io_scene_niftools/license_check.py (keep as Python for easy URL updates)
# - dependencies/ folder (external libraries, not compiled)

modules_to_compile = [
    "io_scene_niftools/addon_updater.py",
    "io_scene_niftools/addon_updater_ops.py",
    "io_scene_niftools/egm_import.py",
    "io_scene_niftools/file_io/__init__.py",
    "io_scene_niftools/file_io/egm.py",
    "io_scene_niftools/file_io/nif.py",
    "io_scene_niftools/kf_export.py",
    "io_scene_niftools/kf_import.py",
    "io_scene_niftools/modules/__init__.py",
    "io_scene_niftools/modules/nif_export/__init__.py",
    "io_scene_niftools/modules/nif_export/animation/__init__.py",
    "io_scene_niftools/modules/nif_export/animation/material.py",
    "io_scene_niftools/modules/nif_export/animation/morph.py",
    "io_scene_niftools/modules/nif_export/animation/object.py",
    "io_scene_niftools/modules/nif_export/animation/shader.py",
    "io_scene_niftools/modules/nif_export/animation/texture.py",
    "io_scene_niftools/modules/nif_export/animation/transform.py",
    "io_scene_niftools/modules/nif_export/armature/__init__.py",
    "io_scene_niftools/modules/nif_export/block_registry.py",
    "io_scene_niftools/modules/nif_export/collision/__init__.py",
    "io_scene_niftools/modules/nif_export/collision/bound.py",
    "io_scene_niftools/modules/nif_export/collision/havok.py",
    "io_scene_niftools/modules/nif_export/constraint/__init__.py",
    "io_scene_niftools/modules/nif_export/geometry/__init__.py",
    "io_scene_niftools/modules/nif_export/geometry/mesh/__init__.py",
    "io_scene_niftools/modules/nif_export/geometry/mesh/skin_partition.py",
    "io_scene_niftools/modules/nif_export/geometry/vertex/__init__.py",
    "io_scene_niftools/modules/nif_export/object/__init__.py",
    "io_scene_niftools/modules/nif_export/property/__init__.py",
    "io_scene_niftools/modules/nif_export/property/material/__init__.py",
    "io_scene_niftools/modules/nif_export/property/object/__init__.py",
    "io_scene_niftools/modules/nif_export/property/shader/__init__.py",
    "io_scene_niftools/modules/nif_export/property/texture/__init__.py",
    "io_scene_niftools/modules/nif_export/property/texture/types/__init__.py",
    "io_scene_niftools/modules/nif_export/property/texture/types/bsshadertexture.py",
    "io_scene_niftools/modules/nif_export/property/texture/types/nitextureprop.py",
    "io_scene_niftools/modules/nif_export/property/texture/writer.py",
    "io_scene_niftools/modules/nif_export/scene/__init__.py",
    "io_scene_niftools/modules/nif_export/types.py",
    "io_scene_niftools/modules/nif_import/__init__.py",
    "io_scene_niftools/modules/nif_import/animation/__init__.py",
    "io_scene_niftools/modules/nif_import/animation/material.py",
    "io_scene_niftools/modules/nif_import/animation/morph.py",
    "io_scene_niftools/modules/nif_import/animation/object.py",
    "io_scene_niftools/modules/nif_import/animation/transform.py",
    "io_scene_niftools/modules/nif_import/armature/__init__.py",
    "io_scene_niftools/modules/nif_import/collision/__init__.py",
    "io_scene_niftools/modules/nif_import/collision/bound.py",
    "io_scene_niftools/modules/nif_import/collision/havok.py",
    "io_scene_niftools/modules/nif_import/constraint/__init__.py",
    "io_scene_niftools/modules/nif_import/geometry/__init__.py",
    "io_scene_niftools/modules/nif_import/geometry/mesh/__init__.py",
    "io_scene_niftools/modules/nif_import/geometry/vertex/__init__.py",
    "io_scene_niftools/modules/nif_import/geometry/vertex/groups.py",
    "io_scene_niftools/modules/nif_import/object/__init__.py",
    "io_scene_niftools/modules/nif_import/object/block_registry.py",
    "io_scene_niftools/modules/nif_import/object/types.py",
    "io_scene_niftools/modules/nif_import/property/__init__.py",
    "io_scene_niftools/modules/nif_import/property/geometry/__init__.py",
    "io_scene_niftools/modules/nif_import/property/geometry/mesh.py",
    "io_scene_niftools/modules/nif_import/property/geometry/niproperty.py",
    "io_scene_niftools/modules/nif_import/property/material/__init__.py",
    "io_scene_niftools/modules/nif_import/property/nodes_wrapper/__init__.py",
    "io_scene_niftools/modules/nif_import/property/object/__init__.py",
    "io_scene_niftools/modules/nif_import/property/shader/__init__.py",
    "io_scene_niftools/modules/nif_import/property/shader/bsshaderlightingproperty.py",
    "io_scene_niftools/modules/nif_import/property/shader/bsshaderproperty.py",
    "io_scene_niftools/modules/nif_import/property/texture/__init__.py",
    "io_scene_niftools/modules/nif_import/property/texture/loader.py",
    "io_scene_niftools/modules/nif_import/property/texture/types/__init__.py",
    "io_scene_niftools/modules/nif_import/property/texture/types/bsshadertexture.py",
    "io_scene_niftools/modules/nif_import/property/texture/types/nitextureprop.py",
    "io_scene_niftools/modules/nif_import/scene/__init__.py",
    "io_scene_niftools/nif_common.py",
    "io_scene_niftools/nif_export.py",
    "io_scene_niftools/nif_import.py",
    "io_scene_niftools/operators/__init__.py",
    "io_scene_niftools/operators/common_op.py",
    "io_scene_niftools/operators/egm_import_op.py",
    "io_scene_niftools/operators/geometry.py",
    "io_scene_niftools/operators/kf_export_op.py",
    "io_scene_niftools/operators/kf_import_op.py",
    "io_scene_niftools/operators/nif_export_op.py",
    "io_scene_niftools/operators/nif_import_op.py",
    "io_scene_niftools/operators/object.py",
    "io_scene_niftools/prefs/__init__.py",
    "io_scene_niftools/properties/__init__.py",
    "io_scene_niftools/properties/armature.py",
    "io_scene_niftools/properties/collision.py",
    "io_scene_niftools/properties/constraint.py",
    "io_scene_niftools/properties/material.py",
    "io_scene_niftools/properties/object.py",
    "io_scene_niftools/properties/scene.py",
    "io_scene_niftools/properties/shader.py",
    "io_scene_niftools/ui/__init__.py",
    "io_scene_niftools/ui/armature.py",
    "io_scene_niftools/ui/collision.py",
    "io_scene_niftools/ui/material.py",
    "io_scene_niftools/ui/object.py",
    "io_scene_niftools/ui/operators/__init__.py",
    "io_scene_niftools/ui/operators/nif_export.py",
    "io_scene_niftools/ui/operators/nif_import.py",
    "io_scene_niftools/ui/scene.py",
    "io_scene_niftools/ui/shader.py",
    "io_scene_niftools/update.py",
    "io_scene_niftools/utils/__init__.py",
    "io_scene_niftools/utils/consts.py",
    "io_scene_niftools/utils/debugging.py",
    "io_scene_niftools/utils/decorators.py",
    "io_scene_niftools/utils/logging.py",
    "io_scene_niftools/utils/math.py",
    "io_scene_niftools/utils/nodes.py",
    "io_scene_niftools/utils/singleton.py",
    "io_scene_niftools/utils/updater/__init__.py",
]

# Convert to Extension objects
extensions = [
    Extension(
        name=module.replace("/", ".").replace("\\", ".").replace(".py", ""),
        sources=[module],
        # Optional: Add compiler directives for optimization
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    )
    for module in modules_to_compile
]

# Cython compiler directives
compiler_directives = {
    'language_level': 3,  # Python 3
    'embedsignature': True,  # Keep docstrings
    'boundscheck': True,  # Keep bounds checking for safety
    'wraparound': True,  # Allow negative indexing (Python behavior)
    'cdivision': False,  # Use Python division (safer)
    # Suppress warnings that are treated as errors
    'warn.undeclared': False,
    'warn.unreachable': False,
    'warn.maybe_uninitialized': False,
}

setup(
    name="blender_niftools_addon",
    version="0.1.1",
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        # Keep .c files for debugging (optional)
        build_dir="build",
    ),
    zip_safe=False,
)
