#!/usr/bin/env python3
"""
Sign model files with HMAC-SHA256 for production integrity verification.

Usage:
    # Sign the production model (v6)
    python scripts/sign_model.py --model models/flood_model_v6.joblib --key <signing_key>

    # Sign using MODEL_SIGNING_KEY env var or Docker secret
    export MODEL_SIGNING_KEY=your-hex-key
    python scripts/sign_model.py --model models/flood_model_v6.joblib

    # Sign all models
    python scripts/sign_model.py --all --key <signing_key>

    # Verify a signed model
    python scripts/sign_model.py --verify --model models/flood_model_v6.joblib --key <signing_key>
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def get_signing_key(key_arg: str | None) -> str:
    """Get signing key from argument, env var, or Docker secret."""
    if key_arg:
        return key_arg

    # Check Docker secret file
    key_file = os.environ.get("MODEL_SIGNING_KEY_FILE")
    if key_file and os.path.isfile(key_file):
        with open(key_file) as f:
            return f.read().strip()

    # Check env var
    key = os.environ.get("MODEL_SIGNING_KEY", "")
    if key:
        return key

    print("ERROR: No signing key provided. Use --key, MODEL_SIGNING_KEY env var, or MODEL_SIGNING_KEY_FILE.")
    sys.exit(1)


def compute_hmac(model_path: Path, signing_key: str) -> str:
    """Compute HMAC-SHA256 of a model file."""
    h = hmac.new(signing_key.encode("utf-8"), digestmod=hashlib.sha256)
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256(model_path: Path) -> str:
    """Compute SHA-256 checksum of a model file."""
    h = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_model(model_path: Path, signing_key: str) -> None:
    """Sign a model and update its metadata JSON."""
    metadata_path = model_path.with_suffix(".json")

    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        sys.exit(1)

    # Load or create metadata
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    # Compute signatures
    hmac_sig = compute_hmac(model_path, signing_key)
    sha256_checksum = compute_sha256(model_path)

    # Update metadata
    metadata["hmac_signature"] = hmac_sig
    metadata["hmac_algorithm"] = "HMAC-SHA256"
    metadata["checksum"] = sha256_checksum
    metadata["checksum_algorithm"] = "SHA-256"

    # Write metadata
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Signed: {model_path.name}")
    print(f"    HMAC-SHA256: {hmac_sig[:16]}...")
    print(f"    SHA-256:     {sha256_checksum[:16]}...")
    print(f"    Metadata:    {metadata_path.name}")


def verify_model(model_path: Path, signing_key: str) -> bool:
    """Verify a model's HMAC signature against its metadata."""
    metadata_path = model_path.with_suffix(".json")

    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        return False

    if not metadata_path.exists():
        print(f"ERROR: Metadata file not found: {metadata_path}")
        return False

    with open(metadata_path) as f:
        metadata = json.load(f)

    expected_sig = metadata.get("hmac_signature")
    if not expected_sig:
        print(f"WARN: No HMAC signature in metadata for {model_path.name}")
        return False

    actual_sig = compute_hmac(model_path, signing_key)
    is_valid = hmac.compare_digest(actual_sig, expected_sig)

    if is_valid:
        print(f"  VALID: {model_path.name}")
    else:
        print(f"  INVALID: {model_path.name}")
        print(f"    Expected: {expected_sig[:16]}...")
        print(f"    Actual:   {actual_sig[:16]}...")

    return is_valid


def main():
    parser = argparse.ArgumentParser(description="Sign or verify model files with HMAC-SHA256")
    parser.add_argument("--model", type=Path, help="Path to model .joblib file")
    parser.add_argument("--all", action="store_true", help="Sign all models in models/ directory")
    parser.add_argument("--verify", action="store_true", help="Verify instead of sign")
    parser.add_argument("--key", type=str, help="HMAC signing key (or set MODEL_SIGNING_KEY env var)")

    args = parser.parse_args()

    if not args.model and not args.all:
        parser.print_help()
        sys.exit(1)

    signing_key = get_signing_key(args.key)

    if args.all:
        models = sorted(MODELS_DIR.glob("*.joblib"))
        if not models:
            print(f"No .joblib files found in {MODELS_DIR}")
            sys.exit(1)

        action = "Verifying" if args.verify else "Signing"
        print(f"\n{action} {len(models)} model(s):\n")

        results = []
        for model in models:
            if args.verify:
                results.append(verify_model(model, signing_key))
            else:
                sign_model(model, signing_key)
                results.append(True)

        if args.verify:
            valid = sum(results)
            print(f"\n{valid}/{len(results)} models verified successfully.")
            sys.exit(0 if all(results) else 1)
        else:
            print(f"\n{len(models)} model(s) signed successfully.")
    else:
        model_path = args.model
        if not model_path.is_absolute():
            model_path = MODELS_DIR / model_path if not model_path.exists() else model_path

        if args.verify:
            success = verify_model(model_path, signing_key)
            sys.exit(0 if success else 1)
        else:
            sign_model(model_path, signing_key)


if __name__ == "__main__":
    main()
