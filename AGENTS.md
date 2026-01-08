# Project Agent Guide

## Project summary
- Blender add-on that imports/exports NetImmerse/Gamebryo formats (`.nif`, `.kf`, `.egm`).
- Core add-on code lives in `io_scene_niftools/` and registers Blender operators, UI, and properties.
- Documentation is in `docs/` and built with Sphinx.
- Release history and user-facing changes are tracked in `CHANGELOG.rst`.
- Build, install, and distribution helpers live in `install/`, `bin/`, `dist_obfuscated/`, and `dependencies/`.

## How to answer questions
- Gather evidence from project files first; rely on blender 4.5's documentation or online niftools documentation only when necessary.
- Explain conclusions by citing the most relevant file paths.
- Provide the correct reference point for each claim (file path, and line/section when helpful).
- Prefer primary sources: `io_scene_niftools/` for behavior, `docs/` for docs, and `CHANGELOG.rst` for history.

## Quick pointers
- Add-on entry point and metadata: `io_scene_niftools/__init__.py`
- Main add-on packages: `io_scene_niftools/`
- Docs root: `docs/index.rst`
- Contribution rules: `CONTRIBUTING.rst`
- Release notes: `CHANGELOG.rst`

## Main functionality: import/export entry points
- NIF import main file: `io_scene_niftools/nif_import.py` (`NifImport.execute` loads NIFs via `NifFile.load_nif`, sets helpers, and walks root blocks through `import_root`/`import_branch` using `io_scene_niftools/modules/nif_import/` helpers).
- NIF export main file: `io_scene_niftools/nif_export.py` (`NifExport.execute` gathers exportable objects, builds the root block via `Object.export_root_node`, applies post-processing, then writes the NIF/EGM output).
- KF import main file: `io_scene_niftools/kf_import.py` (`KfImport.execute` loads .kf files via `NifFile.load_nif`, sets FPS, and imports keyframes via `TransformAnimation.import_kf_root`).
- KF export main file: `io_scene_niftools/kf_export.py` (`KfExport.execute` builds the keyframe tree with `TransformAnimation.export_kf_root` and writes the .kf output).
- Operators wiring: `io_scene_niftools/operators/nif_import_op.py`, `io_scene_niftools/operators/nif_export_op.py`, `io_scene_niftools/operators/kf_import_op.py`, and `io_scene_niftools/operators/kf_export_op.py` instantiate the corresponding classes and call `execute` from the Blender UI.
