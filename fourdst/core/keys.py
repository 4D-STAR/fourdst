# fourdst/core/keys.py
"""
Core key management functions for 4DSTAR.

This module provides the core functionality for managing cryptographic keys
used for bundle signing and verification. All key operations should go through
these functions to maintain consistency between CLI and Electron interfaces.

ARCHITECTURE:
=============
- All functions return JSON-serializable dictionaries
- Progress callbacks are separate from return values
- Consistent error format: {"success": false, "error": "message"}
- Functions handle both interactive and programmatic usage
"""

import os
import sys
import json
import shutil
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization

from fourdst.core.config import FOURDST_CONFIG_DIR, LOCAL_TRUST_STORE_PATH
from fourdst.core.utils import run_command

# Configure logging to go to stderr only, never stdout
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Key management paths
MANUAL_KEYS_DIR = LOCAL_TRUST_STORE_PATH / "manual"
REMOTES_DIR = LOCAL_TRUST_STORE_PATH / "remotes"
KEY_REMOTES_CONFIG = FOURDST_CONFIG_DIR / "key_remotes.json"


def list_keys(progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Lists all trusted public keys organized by source.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "keys": {
                "source_name": [
                    {
                        "name": str,
                        "path": str,
                        "fingerprint": str,
                        "size_bytes": int
                    }
                ]
            },
            "total_count": int
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            logging.info(message)

    try:
        report_progress("Scanning trust store for keys...")
        
        if not LOCAL_TRUST_STORE_PATH.exists():
            return {
                "success": True,
                "keys": {},
                "total_count": 0,
                "message": "Trust store not found - no keys available"
            }

        keys_by_source = {}
        total_count = 0

        for source_dir in LOCAL_TRUST_STORE_PATH.iterdir():
            if source_dir.is_dir():
                source_keys = []
                # Look for both .pub and .pub.pem files
                key_patterns = ["*.pub", "*.pub.pem"]
                for pattern in key_patterns:
                    for key_file in source_dir.glob(pattern):
                        try:
                            fingerprint = _get_key_fingerprint(key_file)
                            key_info = {
                                "name": key_file.name,
                                "path": str(key_file),
                                "fingerprint": fingerprint,
                                "size_bytes": key_file.stat().st_size
                            }
                            source_keys.append(key_info)
                            total_count += 1
                        except Exception as e:
                            report_progress(f"Warning: Could not process key {key_file}: {e}")

                if source_keys:
                    keys_by_source[source_dir.name] = source_keys

        report_progress(f"Found {total_count} keys across {len(keys_by_source)} sources")
        
        return {
            "success": True,
            "keys": keys_by_source,
            "total_count": total_count
        }

    except Exception as e:
        logging.exception(f"Unexpected error listing keys")
        return {
            "success": False,
            "error": f"Failed to list keys: {str(e)}"
        }


def generate_key(
    key_name: str = "author_key",
    key_type: str = "ed25519",
    output_dir: Optional[Path] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Generates a new Ed25519 or RSA key pair for signing bundles.
    
    Args:
        key_name: Base name for the generated key files
        key_type: Type of key to generate ("ed25519" or "rsa")
        output_dir: Directory to save keys (defaults to current directory)
        progress_callback: Optional function for progress updates
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "private_key_path": str,
            "public_key_path": str,
            "openssh_public_key_path": str,
            "key_type": str,
            "fingerprint": str
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            logging.info(message)

    try:
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Define key file paths
        private_key_path = output_dir / f"{key_name}.pem"
        public_key_path = output_dir / f"{key_name}.pub.pem"
        openssh_public_key_path = output_dir / f"{key_name}.pub"

        # Check if files already exist
        if private_key_path.exists() or public_key_path.exists() or openssh_public_key_path.exists():
            return {
                "success": False,
                "error": f"Key files already exist: {private_key_path.name}, {public_key_path.name}, or {openssh_public_key_path.name}"
            }

        # Generate key based on requested type
        key_type = key_type.lower()
        if key_type == "ed25519":
            report_progress("Generating Ed25519 key pair...")
            private_key_obj = ed25519.Ed25519PrivateKey.generate()
        elif key_type == "rsa":
            report_progress("Generating RSA-2048 key pair...")
            private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        else:
            return {
                "success": False,
                "error": f"Unsupported key type: {key_type}. Supported types: ed25519, rsa"
            }

        # Serialize private key to PEM
        report_progress("Writing private key...")
        priv_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_path.write_bytes(priv_pem)

        # Derive and serialize public key to PEM
        report_progress("Writing public key...")
        public_key_obj = private_key_obj.public_key()
        pub_pem = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_path.write_bytes(pub_pem)

        # Also write OpenSSH-compatible public key
        openssh_pub = public_key_obj.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        openssh_public_key_path.write_bytes(openssh_pub)

        # Generate fingerprint
        fingerprint = _get_key_fingerprint(public_key_path)

        report_progress("Key generation completed successfully!")

        return {
            "success": True,
            "private_key_path": str(private_key_path.resolve()),
            "public_key_path": str(public_key_path.resolve()),
            "openssh_public_key_path": str(openssh_public_key_path.resolve()),
            "key_type": key_type,
            "fingerprint": fingerprint,
            "message": f"Generated {key_type.upper()} key pair successfully"
        }

    except Exception as e:
        logging.exception(f"Unexpected error generating key")
        return {
            "success": False,
            "error": f"Failed to generate key: {str(e)}"
        }


def add_key(
    key_path: Path,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Adds a single public key to the local trust store.
    
    Args:
        key_path: Path to the public key file to add
        progress_callback: Optional function for progress updates
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "key_name": str,
            "fingerprint": str,
            "destination_path": str,
            "already_existed": bool
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            logging.info(message)

    try:
        key_path = Path(key_path)
        
        if not key_path.exists():
            return {
                "success": False,
                "error": f"Key file does not exist: {key_path}"
            }

        if not key_path.is_file():
            return {
                "success": False,
                "error": f"Path is not a file: {key_path}"
            }

        # Ensure manual keys directory exists
        MANUAL_KEYS_DIR.mkdir(parents=True, exist_ok=True)
        
        destination = MANUAL_KEYS_DIR / key_path.name
        already_existed = False

        if destination.exists():
            # Check if content is identical
            if destination.read_bytes() == key_path.read_bytes():
                already_existed = True
                report_progress(f"Key '{key_path.name}' already exists with identical content")
            else:
                return {
                    "success": False,
                    "error": f"Key '{key_path.name}' already exists with different content"
                }
        else:
            report_progress(f"Adding key '{key_path.name}' to trust store...")
            shutil.copy(key_path, destination)

        # Generate fingerprint
        fingerprint = _get_key_fingerprint(destination)

        return {
            "success": True,
            "key_name": key_path.name,
            "fingerprint": fingerprint,
            "destination_path": str(destination),
            "already_existed": already_existed,
            "message": f"Key '{key_path.name}' {'already exists in' if already_existed else 'added to'} trust store"
        }

    except Exception as e:
        logging.exception(f"Unexpected error adding key")
        return {
            "success": False,
            "error": f"Failed to add key: {str(e)}"
        }


def remove_key(
    key_identifier: str,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Removes a key from the trust store by fingerprint, name, or path.
    
    Args:
        key_identifier: Key fingerprint, name, or path to identify the key to remove
        progress_callback: Optional function for progress updates
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "removed_keys": [
                {
                    "name": str,
                    "path": str,
                    "source": str
                }
            ],
            "removed_count": int
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            logging.info(message)

    try:
        if not LOCAL_TRUST_STORE_PATH.exists():
            return {
                "success": False,
                "error": "Trust store not found"
            }

        removed_keys = []
        
        # Search for matching keys (same patterns as list_keys)
        for source_dir in LOCAL_TRUST_STORE_PATH.iterdir():
            if source_dir.is_dir():
                key_patterns = ["*.pub", "*.pub.pem"]
                for pattern in key_patterns:
                    for key_file in source_dir.glob(pattern):
                        should_remove = False
                        
                        # Check if identifier matches fingerprint, name, or path
                        try:
                            fingerprint = _get_key_fingerprint(key_file)
                            if (key_identifier == fingerprint or 
                                key_identifier == key_file.name or 
                                key_identifier == str(key_file) or
                                key_identifier == str(key_file.resolve())):
                                should_remove = True
                        except Exception as e:
                            report_progress(f"Warning: Could not process key {key_file}: {e}")
                            continue
                        
                        if should_remove:
                            report_progress(f"Removing key '{key_file.name}' from source '{source_dir.name}'")
                            removed_keys.append({
                                "name": key_file.name,
                                "path": str(key_file),
                                "source": source_dir.name
                            })
                            key_file.unlink()

        if not removed_keys:
            return {
                "success": False,
                "error": f"No matching key found for identifier: {key_identifier}"
            }

        return {
            "success": True,
            "removed_keys": removed_keys,
            "removed_count": len(removed_keys),
            "message": f"Removed {len(removed_keys)} key(s)"
        }

    except Exception as e:
        logging.exception(f"Unexpected error removing key")
        return {
            "success": False,
            "error": f"Failed to remove key: {str(e)}"
        }


def sync_remotes(progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Syncs the local trust store with all configured remote Git repositories.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "synced_remotes": [
                {
                    "name": str,
                    "url": str,
                    "status": "success" | "failed",
                    "error": str (if failed)
                }
            ],
            "removed_remotes": [str],  # Names of remotes that were removed due to failures
            "total_keys_synced": int
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            logging.info(message)

    try:
        if not KEY_REMOTES_CONFIG.exists():
            return {
                "success": False,
                "error": "No remotes configured. Use remote management to add remotes first."
            }

        with open(KEY_REMOTES_CONFIG, 'r') as f:
            config = json.load(f)
        
        remotes = config.get("remotes", [])
        if not remotes:
            return {
                "success": False,
                "error": "No remotes configured in config file"
            }

        REMOTES_DIR.mkdir(parents=True, exist_ok=True)
        
        synced_remotes = []
        remotes_to_remove = []
        total_keys_synced = 0

        for remote in remotes:
            name = remote['name']
            url = remote['url']
            remote_path = REMOTES_DIR / name
            
            report_progress(f"Syncing remote '{name}' from {url}")
            
            try:
                if remote_path.exists():
                    run_command(["git", "pull"], cwd=remote_path)
                else:
                    run_command(["git", "clone", "--depth", "1", url, str(remote_path)])
                
                # Clean up non-public key files and count keys
                keys_count = 0
                for item in remote_path.rglob("*"):
                    if item.is_file():
                        if item.suffix == '.pub':
                            keys_count += 1
                        else:
                            item.unlink()
                
                total_keys_synced += keys_count
                
                synced_remotes.append({
                    "name": name,
                    "url": url,
                    "status": "success",
                    "keys_count": keys_count
                })
                
                report_progress(f"Successfully synced '{name}' ({keys_count} keys)")

            except Exception as e:
                error_msg = str(e)
                synced_remotes.append({
                    "name": name,
                    "url": url,
                    "status": "failed",
                    "error": error_msg
                })
                remotes_to_remove.append(name)
                report_progress(f"Failed to sync remote '{name}': {error_msg}")

        # Remove failed remotes from config if any
        if remotes_to_remove:
            config['remotes'] = [r for r in config['remotes'] if r['name'] not in remotes_to_remove]
            with open(KEY_REMOTES_CONFIG, 'w') as f:
                json.dump(config, f, indent=2)

        success_count = len([r for r in synced_remotes if r["status"] == "success"])
        
        return {
            "success": True,
            "synced_remotes": synced_remotes,
            "removed_remotes": remotes_to_remove,
            "total_keys_synced": total_keys_synced,
            "message": f"Sync completed: {success_count} successful, {len(remotes_to_remove)} failed"
        }

    except Exception as e:
        logging.exception(f"Unexpected error syncing remotes")
        return {
            "success": False,
            "error": f"Failed to sync remotes: {str(e)}"
        }


def get_remote_sources(progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Lists all configured remote key sources.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "remotes": [
                {
                    "name": str,
                    "url": str,
                    "local_path": str,
                    "exists": bool,
                    "keys_count": int
                }
            ]
        }
    """
    try:
        if not KEY_REMOTES_CONFIG.exists():
            return {
                "success": True,
                "remotes": [],
                "message": "No remotes configured"
            }

        with open(KEY_REMOTES_CONFIG, 'r') as f:
            config = json.load(f)
        
        remotes_info = []
        for remote in config.get("remotes", []):
            remote_path = REMOTES_DIR / remote['name']
            keys_count = len(list(remote_path.glob("*.pub"))) if remote_path.exists() else 0
            
            remotes_info.append({
                "name": remote['name'],
                "url": remote['url'],
                "local_path": str(remote_path),
                "exists": remote_path.exists(),
                "keys_count": keys_count
            })

        return {
            "success": True,
            "remotes": remotes_info
        }

    except Exception as e:
        logging.exception(f"Unexpected error getting remote sources")
        return {
            "success": False,
            "error": f"Failed to get remote sources: {str(e)}"
        }


def add_remote_source(
    name: str,
    url: str,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Adds a new remote key source.
    
    Args:
        name: Name for the remote source
        url: Git repository URL
        progress_callback: Optional function for progress updates
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "name": str,
            "url": str,
            "message": str
        }
    """
    try:
        FOURDST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new one
        config = {"remotes": []}
        if KEY_REMOTES_CONFIG.exists():
            with open(KEY_REMOTES_CONFIG, 'r') as f:
                config = json.load(f)

        # Check if remote already exists
        for remote in config.get("remotes", []):
            if remote['name'] == name:
                return {
                    "success": False,
                    "error": f"Remote '{name}' already exists"
                }

        # Add new remote
        config.setdefault("remotes", []).append({
            "name": name,
            "url": url
        })

        # Save config
        with open(KEY_REMOTES_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)

        return {
            "success": True,
            "name": name,
            "url": url,
            "message": f"Remote '{name}' added successfully"
        }

    except Exception as e:
        logging.exception(f"Unexpected error adding remote source")
        return {
            "success": False,
            "error": f"Failed to add remote source: {str(e)}"
        }


def remove_remote_source(
    name: str,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Removes a remote key source.
    
    Args:
        name: Name of the remote source to remove
        progress_callback: Optional function for progress updates
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "name": str,
            "message": str
        }
    """
    try:
        if not KEY_REMOTES_CONFIG.exists():
            return {
                "success": False,
                "error": "No remotes configured"
            }

        with open(KEY_REMOTES_CONFIG, 'r') as f:
            config = json.load(f)

        original_len = len(config.get("remotes", []))
        config["remotes"] = [r for r in config.get("remotes", []) if r['name'] != name]

        if len(config["remotes"]) == original_len:
            return {
                "success": False,
                "error": f"Remote '{name}' not found"
            }

        # Save updated config
        with open(KEY_REMOTES_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)

        # Remove local directory if it exists
        remote_path = REMOTES_DIR / name
        if remote_path.exists():
            shutil.rmtree(remote_path)

        return {
            "success": True,
            "name": name,
            "message": f"Remote '{name}' removed successfully"
        }

    except Exception as e:
        logging.exception(f"Unexpected error removing remote source")
        return {
            "success": False,
            "error": f"Failed to remove remote source: {str(e)}"
        }


def _get_key_fingerprint(key_path: Path) -> str:
    """
    Generates a SHA256 fingerprint for a public key.
    
    Args:
        key_path: Path to the public key file
        
    Returns:
        SHA256 fingerprint in format "sha256:hexdigest"
    """
    pub_key_bytes = key_path.read_bytes()
    return "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()
