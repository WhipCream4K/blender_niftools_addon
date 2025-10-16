#!/usr/bin/env python3
"""
Generate a list of all Python modules in io_scene_niftools for compilation.
This script scans the directory and creates the module list for setup.py.
"""

import os
from pathlib import Path

def find_all_python_files(root_dir="io_scene_niftools"):
    """Find all .py files in the io_scene_niftools directory."""
    python_files = []
    root_path = Path(root_dir)
    
    for py_file in root_path.rglob("*.py"):
        # Convert to relative path string with forward slashes
        rel_path = str(py_file.relative_to(root_path.parent))
        python_files.append(rel_path.replace("\\", "/"))
    
    return sorted(python_files)

def main():
    """Generate and display the module list."""
    print("Scanning io_scene_niftools for Python files...\n")
    
    modules = find_all_python_files()
    
    print(f"Found {len(modules)} Python files:\n")
    print("# Copy this list to setup.py and build_release.py")
    print("# in the COMPILED_MODULES variable\n")
    print("COMPILED_MODULES = [")
    for module in modules:
        print(f'    "{module}",')
    print("]")
    
    print(f"\n✅ Total modules to compile: {len(modules)}")
    print("\n⚠️  Note: You may want to exclude certain files like:")
    print("   - __init__.py at the root (Blender needs to read bl_info)")
    print("   - UI/operator registration files (if they use decorators)")

if __name__ == "__main__":
    main()
