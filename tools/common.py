"""Shared helpers for the OSRS Guide Company toolchain.

Standard library only, so every agent's environment can run it without
installing anything. Every tool resolves paths relative to the project root.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OSRS_COMPANY_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR")
            or Path(__file__).resolve().parent.parent).resolve()
JOBS = ROOT / "jobs"
SCHEMAS = ROOT / "schemas"
TEMPLATES = ROOT / "templates"
CACHE = ROOT / "cache"

JOB_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return _dt.date.today().isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(obj) -> str:
    """Stable serialisation used for hashing structured data."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def job_dir(job_id: str) -> Path:
    if not JOB_ID_RE.match(job_id):
        die(f"invalid job id {job_id!r}: use lowercase letters, digits and hyphens")
    return JOBS / job_id


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# Minimal JSON-Schema validator (draft-07 subset). Supports: type, enum,
# const, required, properties, additionalProperties(bool|schema), items,
# minItems, maxItems, minimum, maximum, minLength, maxLength, pattern,
# anyOf, oneOf, $ref to "#/definitions/...". Enough for our handoff contracts.
# --------------------------------------------------------------------------
_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def validate_schema(instance, schema, root=None, path="$") -> list[str]:
    root = root or schema
    errs: list[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return [f"{path}: unsupported $ref {ref}"]
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        return validate_schema(instance, target, root, path)
    if "anyOf" in schema:
        if not any(not validate_schema(instance, s, root, path) for s in schema["anyOf"]):
            errs.append(f"{path}: does not match any allowed shape")
        return errs
    if "oneOf" in schema:
        n = sum(1 for s in schema["oneOf"] if not validate_schema(instance, s, root, path))
        if n != 1:
            errs.append(f"{path}: must match exactly one allowed shape (matched {n})")
        return errs
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(instance, x) for x in types):
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: {instance!r} does not match /{schema['pattern']}/")
    if _is_type(instance, "number"):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: at most {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs += validate_schema(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: missing required field '{key}'")
        props = schema.get("properties", {})
        for key, val in instance.items():
            if key in props:
                errs += validate_schema(val, props[key], root, f"{path}.{key}")
            else:
                ap = schema.get("additionalProperties", True)
                if ap is False:
                    errs.append(f"{path}: unexpected field '{key}'")
                elif isinstance(ap, dict):
                    errs += validate_schema(val, ap, root, f"{path}.{key}")
    return errs


def validate_against(instance, schema_name: str) -> list[str]:
    schema = load_json(SCHEMAS / f"{schema_name}.schema.json")
    return validate_schema(instance, schema)
