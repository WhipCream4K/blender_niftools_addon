# Project Agent Guide

## Project summary
- Blender add-on that imports/exports NetImmerse/Gamebryo formats (`.nif`, `.kf`, `.egm`).
- Core add-on code lives in `io_scene_niftools/` and registers Blender operators, UI, and properties.
- Documentation is in `docs/` and built with Sphinx.
- Release history and user-facing changes are tracked in `CHANGELOG.rst`.
- Build, install, and distribution helpers live in `install/`, `bin/`, `dist_obfuscated/`, and `dependencies/`.

## Source of truth
When answering questions, use only information from this repository.
If a question cannot be answered from this repository, say so and ask for a specific file or pointer.

## How to answer questions
- Gather evidence from project files only; do not rely on external knowledge.
- Explain conclusions by citing the most relevant file paths.
- Provide the correct reference point for each claim (file path, and line/section when helpful).
- Prefer primary sources: `io_scene_niftools/` for behavior, `docs/` for docs, and `CHANGELOG.rst` for history.

## Quick pointers
- Add-on entry point and metadata: `io_scene_niftools/__init__.py`
- Main add-on packages: `io_scene_niftools/`
- Docs root: `docs/index.rst`
- Contribution rules: `CONTRIBUTING.rst`
- Release notes: `CHANGELOG.rst`
