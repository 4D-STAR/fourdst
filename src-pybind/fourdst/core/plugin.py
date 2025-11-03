# fourdst/core/plugin.py

import yaml
import zipfile
import shutil
import tempfile
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from fourdst.cli.common.utils import calculate_sha256, run_command, get_template_content
from fourdst.cli.common.templates import GITIGNORE_CONTENT


def parse_cpp_interface(header_path: Path) -> Dict[str, Any]:
    """
    Parses a C++ header file using libclang to find classes and their pure virtual methods.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "interface_name": [
                    {"signature": str, "body": str},
                    ...
                ]
            },
            "error": str (if success=False)
        }
    """
    try:
        # Import libclang
        try:
            from clang import cindex
        except ImportError:
            return {
                'success': False,
                'error': "The 'init' command requires 'libclang'. Please install it with: pip install python-clang-16"
            }
            
        if not cindex.Config.loaded:
            try:
                cindex.Config.set_library_file(cindex.conf.get_filename())
            except cindex.LibclangError as e:
                return {
                    'success': False,
                    'error': f"libclang library not found. Please ensure it's installed and in your system's path. Details: {e}"
                }

        index = cindex.Index.create()
        args = ['-x', 'c++', '-std=c++17']
        translation_unit = index.parse(str(header_path), args=args)

        if not translation_unit:
            return {
                'success': False,
                'error': f"Unable to parse the translation unit {header_path}"
            }

        interfaces = {}

        def walk_ast(node):
            if node.kind == cindex.CursorKind.CLASS_DECL and node.is_definition():
                pv_methods = [m for m in node.get_children()
                              if m.kind == cindex.CursorKind.CXX_METHOD and m.is_pure_virtual_method()]
                
                if pv_methods:
                    interface_name = node.spelling
                    methods = []
                    for method in pv_methods:
                        args_str = ', '.join([arg.type.spelling for arg in method.get_arguments()])
                        sig = f"{method.result_type.spelling} {method.spelling}({args_str})"
                        
                        if method.is_const_method():
                             sig += " const"

                        methods.append({
                            "signature": sig, 
                            "body": "      // TODO: Implement this method"
                        })
                    
                    interfaces[interface_name] = methods

            for child in node.get_children():
                walk_ast(child)

        walk_ast(translation_unit.cursor)
        
        return {
            'success': True,
            'data': interfaces
        }
        
    except Exception as e:
        logging.exception(f"Unexpected error parsing C++ header {header_path}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def generate_plugin_project(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a new plugin project from configuration.
    
    Args:
        config: {
            "project_name": str,
            "header_path": Path,
            "directory": Path,
            "version": str,
            "libplugin_rev": str,
            "chosen_interface": str,
            "interfaces": dict  # from parse_cpp_interface
        }
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "project_path": str,
                "files_created": [str, ...]
            },
            "error": str (if success=False)
        }
    """
    try:
        project_name = config['project_name']
        header_path = Path(config['header_path'])  # Convert string to Path object
        directory = Path(config['directory'])      # Convert string to Path object
        version = config['version']
        libplugin_rev = config['libplugin_rev']
        chosen_interface = config['chosen_interface']
        interfaces = config['interfaces']

        # Generate method stubs
        method_stubs = "\n".join(
            f"    {method['signature']} override {{\n{method['body']}\n    }}"
            for method in interfaces[chosen_interface]
        )

        class_name = ''.join(filter(str.isalnum, project_name.replace('_', ' ').title().replace(' ', ''))) + "Plugin"
        root_path = directory / project_name
        src_path = root_path / "src"
        include_path = src_path / "include"
        subprojects_path = root_path / "subprojects"
        
        files_created = []

        # Create directory structure
        src_path.mkdir(parents=True, exist_ok=True)
        include_path.mkdir(exist_ok=True)
        subprojects_path.mkdir(exist_ok=True)

        # Copy interface header
        local_header_path = include_path / header_path.name
        shutil.copy(header_path, local_header_path)
        files_created.append(str(local_header_path.relative_to(root_path)))

        # Create libplugin.wrap file
        libplugin_wrap_content = f"""[wrap-git]
url = https://github.com/4D-STAR/libplugin
revision = {libplugin_rev}
depth = 1
"""
        wrap_file = subprojects_path / "libplugin.wrap"
        wrap_file.write_text(libplugin_wrap_content)
        files_created.append(str(wrap_file.relative_to(root_path)))

        # Create meson.build from template
        meson_template = get_template_content("meson.build.in")
        meson_content = meson_template.format(
            project_name=project_name,
            version=version
        )
        meson_file = root_path / "meson.build"
        meson_file.write_text(meson_content)
        files_created.append(str(meson_file.relative_to(root_path)))

        # Create C++ source file from template
        cpp_template = get_template_content("plugin.cpp.in")
        cpp_content = cpp_template.format(
            class_name=class_name,
            project_name=project_name,
            interface=chosen_interface,
            interface_header_path=header_path.name,
            method_stubs=method_stubs
        )
        cpp_file = src_path / f"{project_name}.cpp"
        cpp_file.write_text(cpp_content)
        files_created.append(str(cpp_file.relative_to(root_path)))

        # Create .gitignore
        gitignore_file = root_path / ".gitignore"
        gitignore_file.write_text(GITIGNORE_CONTENT)
        files_created.append(str(gitignore_file.relative_to(root_path)))

        # Initialize Git Repository
        run_command(["git", "init"], cwd=root_path)
        run_command(["git", "add", "."], cwd=root_path)
        commit_message = f"Initial commit: Scaffold fourdst plugin '{project_name}'"
        run_command(["git", "commit", "-m", commit_message], cwd=root_path)

        return {
            'success': True,
            'data': {
                'project_path': str(root_path),
                'files_created': files_created
            }
        }

    except Exception as e:
        logging.exception(f"Unexpected error generating plugin project")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def validate_bundle_directory(directory: Path) -> Dict[str, Any]:
    """
    Validates that a directory has the structure of a valid bundle.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "errors": [str, ...],
                "is_signed": bool
            },
            "error": str (if success=False)
        }
    """
    try:
        errors = []
        manifest_path = directory / "manifest.yaml"

        if not manifest_path.is_file():
            errors.append("Missing 'manifest.yaml' in the root of the directory.")
            return {
                'success': True,
                'data': {
                    'errors': errors,
                    'is_signed': False
                }
            }

        try:
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in manifest.yaml: {e}")
            return {
                'success': True,
                'data': {
                    'errors': errors,
                    'is_signed': False
                }
            }

        # Check that all files referenced in the manifest exist
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            sdist_info = plugin_data.get('sdist', {})
            if sdist_info:
                sdist_path = sdist_info.get('path')
                if sdist_path and not (directory / sdist_path).is_file():
                    errors.append(f"Missing sdist file for '{plugin_name}': {sdist_path}")
            
            for binary in plugin_data.get('binaries', []):
                binary_path = binary.get('path')
                if binary_path and not (directory / binary_path).is_file():
                    errors.append(f"Missing binary file for '{plugin_name}': {binary_path}")
                
                # If checksums exist, validate them
                expected_checksum = binary.get('checksum')
                if binary_path and expected_checksum:
                    file_to_check = directory / binary_path
                    if file_to_check.is_file():
                        actual_checksum = "sha256:" + calculate_sha256(file_to_check)
                        if actual_checksum != expected_checksum:
                            errors.append(f"Checksum mismatch for '{binary_path}'")

        # Check if bundle is signed
        is_signed = ('bundleAuthorKeyFingerprint' in manifest and 
                    (directory / "manifest.sig").exists())

        return {
            'success': True,
            'data': {
                'errors': errors,
                'is_signed': is_signed
            }
        }

    except Exception as e:
        logging.exception(f"Unexpected error validating bundle directory {directory}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def pack_bundle_directory(directory: Path, output_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Packs a directory into a .fbundle archive.
    
    Args:
        directory: Path to directory to pack
        output_config: {
            "name": str (optional, defaults to directory name),
            "output_dir": Path (optional, defaults to directory.parent)
        }
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "output_path": str,
                "is_signed": bool,
                "files_packed": int
            },
            "error": str (if success=False)
        }
    """
    try:
        # First validate the directory
        validation_result = validate_bundle_directory(directory)
        if not validation_result['success']:
            return validation_result
        
        if validation_result['data']['errors']:
            return {
                'success': False,
                'error': f"Validation failed: {'; '.join(validation_result['data']['errors'])}"
            }

        output_name = output_config.get('name', directory.name)
        output_dir = output_config.get('output_dir', directory.parent)
        output_path = output_dir / f"{output_name}.fbundle"

        files_packed = 0
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_to_add in directory.rglob('*'):
                if file_to_add.is_file():
                    arcname = file_to_add.relative_to(directory)
                    bundle_zip.write(file_to_add, arcname)
                    files_packed += 1

        return {
            'success': True,
            'data': {
                'output_path': str(output_path.resolve()),
                'is_signed': validation_result['data']['is_signed'],
                'files_packed': files_packed
            }
        }

    except Exception as e:
        logging.exception(f"Unexpected error packing bundle directory {directory}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def extract_plugin_from_bundle(bundle_path: Path, plugin_name: str, output_path: Path) -> Dict[str, Any]:
    """
    Extracts a plugin's source code from a bundle.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "output_path": str,
                "plugin_info": dict
            },
            "error": str (if success=False)
        }
    """
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # Unpack the main bundle
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(temp_dir)

            # Read the manifest
            manifest_path = temp_dir / "manifest.yaml"
            if not manifest_path.exists():
                return {
                    'success': False,
                    'error': "Bundle is invalid. Missing manifest.yaml."
                }
            
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            # Find the plugin and its sdist
            plugin_data = manifest.get('bundlePlugins', {}).get(plugin_name)
            if not plugin_data:
                available_plugins = list(manifest.get('bundlePlugins', {}).keys())
                return {
                    'success': False,
                    'error': f"Plugin '{plugin_name}' not found in the bundle. Available plugins: {', '.join(available_plugins) if available_plugins else 'none'}"
                }

            sdist_info = plugin_data.get('sdist')
            if not sdist_info or 'path' not in sdist_info:
                return {
                    'success': False,
                    'error': f"Source distribution (sdist) not found for plugin '{plugin_name}'."
                }

            sdist_path_in_bundle = temp_dir / sdist_info['path']
            if not sdist_path_in_bundle.is_file():
                return {
                    'success': False,
                    'error': f"sdist file '{sdist_info['path']}' is missing from the bundle archive."
                }

            # Extract the sdist to the final output directory
            final_destination = output_path / plugin_name
            final_destination.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(sdist_path_in_bundle, 'r') as sdist_zip:
                sdist_zip.extractall(final_destination)

            return {
                'success': True,
                'data': {
                    'output_path': str(final_destination.resolve()),
                    'plugin_info': plugin_data
                }
            }

    except zipfile.BadZipFile:
        return {
            'success': False,
            'error': f"'{bundle_path}' is not a valid bundle (zip) file."
        }
    except Exception as e:
        logging.exception(f"Unexpected error extracting plugin {plugin_name} from {bundle_path}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def compare_plugin_sources(bundle_a_path: Path, bundle_b_path: Path, plugin_name: str) -> Dict[str, Any]:
    """
    Compares the source code of a specific plugin between two different bundles.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "has_changes": bool,
                "added_files": [str, ...],
                "removed_files": [str, ...],
                "modified_files": [
                    {
                        "file_path": str,
                        "diff": str
                    },
                    ...
                ]
            },
            "error": str (if success=False)
        }
    """
    try:
        def extract_sdist(bundle_path: Path, plugin_name: str, temp_dir: Path):
            """Helper function to extract sdist from bundle."""
            sdist_extract_path = temp_dir / f"{plugin_name}_src"
            
            with tempfile.TemporaryDirectory() as bundle_unpack_dir_str:
                bundle_unpack_dir = Path(bundle_unpack_dir_str)
                
                with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                    bundle_zip.extractall(bundle_unpack_dir)
                    
                manifest_path = bundle_unpack_dir / "manifest.yaml"
                if not manifest_path.exists():
                    raise FileNotFoundError("manifest.yaml not found in bundle.")
                    
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
                    
                plugin_data = manifest.get('bundlePlugins', {}).get(plugin_name)
                if not plugin_data or 'sdist' not in plugin_data:
                    raise FileNotFoundError(f"Plugin '{plugin_name}' or its sdist not found in {bundle_path.name}.")
                    
                sdist_path_in_bundle = bundle_unpack_dir / plugin_data['sdist']['path']
                if not sdist_path_in_bundle.exists():
                    raise FileNotFoundError(f"sdist archive '{plugin_data['sdist']['path']}' not found in bundle.")
                    
                with zipfile.ZipFile(sdist_path_in_bundle, 'r') as sdist_zip:
                    sdist_zip.extractall(sdist_extract_path)
                    
            return sdist_extract_path

        with tempfile.TemporaryDirectory() as temp_a_str, tempfile.TemporaryDirectory() as temp_b_str:
            try:
                src_a_path = extract_sdist(bundle_a_path, plugin_name, Path(temp_a_str))
                src_b_path = extract_sdist(bundle_b_path, plugin_name, Path(temp_b_str))
            except FileNotFoundError as e:
                return {
                    'success': False,
                    'error': str(e)
                }

            files_a = {p.relative_to(src_a_path) for p in src_a_path.rglob('*') if p.is_file()}
            files_b = {p.relative_to(src_b_path) for p in src_b_path.rglob('*') if p.is_file()}

            added_files = list(sorted(files_b - files_a))
            removed_files = list(sorted(files_a - files_b))
            common_files = files_a & files_b
            
            modified_files = []
            for file_rel_path in sorted(list(common_files)):
                content_a = (src_a_path / file_rel_path).read_text()
                content_b = (src_b_path / file_rel_path).read_text()

                if content_a != content_b:
                    diff = ''.join(difflib.unified_diff(
                        content_a.splitlines(keepends=True),
                        content_b.splitlines(keepends=True),
                        fromfile=f"a/{file_rel_path}",
                        tofile=f"b/{file_rel_path}",
                    ))
                    modified_files.append({
                        'file_path': str(file_rel_path),
                        'diff': diff
                    })

            has_changes = bool(added_files or removed_files or modified_files)

            return {
                'success': True,
                'data': {
                    'has_changes': has_changes,
                    'added_files': [str(f) for f in added_files],
                    'removed_files': [str(f) for f in removed_files],
                    'modified_files': modified_files
                }
            }

    except Exception as e:
        logging.exception(f"Unexpected error comparing plugin {plugin_name} between bundles")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def validate_plugin_project(project_path: Path) -> Dict[str, Any]:
    """
    Validates a plugin's structure and meson.build file.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "errors": [str, ...],
                "warnings": [str, ...],
                "checks": [
                    {
                        "name": str,
                        "passed": bool,
                        "is_warning": bool,
                        "message": str
                    },
                    ...
                ]
            },
            "error": str (if success=False)
        }
    """
    try:
        # Convert string path to Path object if needed
        if isinstance(project_path, str):
            project_path = Path(project_path)
            
        errors = []
        warnings = []
        checks = []

        def check(condition, name, success_msg, error_msg, is_warning=False):
            passed = bool(condition)
            checks.append({
                'name': name,
                'passed': passed,
                'is_warning': is_warning,
                'message': success_msg if passed else error_msg
            })
            
            if not passed:
                if is_warning:
                    warnings.append(error_msg)
                else:
                    errors.append(error_msg)
            
            return passed

        # Check for meson.build
        meson_file = project_path / "meson.build"
        meson_content = ""
        if check(meson_file.exists(), "meson_build_exists", "Found meson.build file.", "Missing meson.build file."):
            meson_content = meson_file.read_text()
            # Check for project() definition
            check("project(" in meson_content, "has_project_definition", "Contains project() definition.", "meson.build is missing a project() definition.", is_warning=True)
            # Check for shared_library()
            check("shared_library(" in meson_content, "has_shared_library", "Contains shared_library() definition.", "meson.build does not appear to define a shared_library().")

        # Check for source files
        has_cpp = any(project_path.rglob("*.cpp"))
        has_h = any(project_path.rglob("*.h")) or any(project_path.rglob("*.hpp"))
        check(has_cpp, "has_cpp_files", "Found C++ source files (.cpp).", "No .cpp source files found in the directory.", is_warning=True)
        check(has_h, "has_header_files", "Found C++ header files (.h/.hpp).", "No .h or .hpp header files found in the directory.", is_warning=True)

        # Check for test definition (optional)
        check("test(" in meson_content, "has_tests", "Contains test() definitions.", "No test() definitions found in meson.build. Consider adding tests.", is_warning=True)

        return {
            'success': True,
            'data': {
                'errors': errors,
                'warnings': warnings,
                'checks': checks
            }
        }

    except Exception as e:
        logging.exception(f"Unexpected error validating plugin project {project_path}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }
