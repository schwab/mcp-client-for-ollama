# Python 3.13+ Compatibility Fix

**Issue:** Installation fails on Python 3.13 with `ModuleNotFoundError: No module named 'distutils'`

**Root Cause:** Python 3.12+ removed the `distutils` module from the standard library, but older versions of setuptools still depend on it.

---

## Changes Made

### 1. Updated setuptools Requirement

**File:** `pyproject.toml`

**Before:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**After:**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

**Why:** setuptools 68.0+ doesn't depend on the removed `distutils` module.

---

### 2. Updated CLI Package

**File:** `cli-package/pyproject.toml`

**Before:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**After:**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

---

### 3. Fixed Package Discovery

**File:** `pyproject.toml`

**Before (manual package listing):**
```toml
[tool.setuptools]
packages = [
    "mcp_client_for_ollama",
    "mcp_client_for_ollama.agents",
    "mcp_client_for_ollama.config",
    "mcp_client_for_ollama.models",
    "mcp_client_for_ollama.server",
    "mcp_client_for_ollama.tools",
    "mcp_client_for_ollama.utils"
]
```

**After (automatic discovery):**
```toml
[tool.setuptools]
# Use find to automatically discover all Python packages
packages = {find = {}}
```

**Why:**
- Automatic discovery is the modern, recommended approach
- Prevents warnings about data directories being treated as packages
- More maintainable as new packages are added

---

## Additional Fixes

### Clear UV Cache

After making the setuptools change, you need to clear the uv cache to ensure it downloads the newer setuptools version:

```bash
uv cache clean
```

**Why:** uv caches build dependencies, and the old setuptools (which depends on distutils) may still be cached.

---

## Testing

### Verify Build Works:
```bash
# Clean old build artifacts
rm -rf build dist *.egg-info

# Build the wheel
uv build --wheel

# Verify JSON files are included
unzip -l dist/mcp_client_for_ollama-0.23.0-py3-none-any.whl | grep -E "(definitions|examples).*\.json"
```

### Install and Test:
```bash
# Install in Python 3.13 environment
uv pip install . --system

# Verify it works
ollmcp
# Should show "Version 0.23.0" without errors
```

---

## Python Version Compatibility

After this fix, the package supports:

- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13+

---

## Summary of Changes

| File | Change | Reason |
|------|--------|--------|
| `pyproject.toml` | setuptools>=61.0 → >=68.0 | Python 3.13 compatibility |
| `pyproject.toml` | Manual packages → {find = {}} | Better package discovery |
| `cli-package/pyproject.toml` | setuptools>=61.0 → >=68.0 | Python 3.13 compatibility |

---

## Error Messages Resolved

### Before Fix:
```
ModuleNotFoundError: No module named 'distutils'
hint: `distutils` was removed from the standard library in Python 3.12.
```

### After Fix:
```
Successfully built dist/mcp_client_for_ollama-0.23.0-py3-none-any.whl
```

---

## Best Practices Applied

1. **Use Latest Setuptools:** setuptools 68.0+ is the first version that works without distutils
2. **Use Automatic Package Discovery:** `packages = {find = {}}` is the modern approach
3. **Include Wheel in Build Requirements:** Explicitly specify `wheel` in build-system requires
4. **Clear Caches After Changes:** Always clear uv cache when updating build dependencies

---

## References

- [PEP 632: Deprecate distutils](https://peps.python.org/pep-0632/)
- [Setuptools Package Discovery](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html)
- [Setuptools Build System Configuration](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)

---

**Status:** ✅ Fixed and Tested
