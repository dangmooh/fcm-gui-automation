"""
App Profile Generator

Launch a selected Windows GUI application, extract UIA controls with pywinauto,
save YAML draft profiles, and create annotated screenshots.
"""

from pathlib import Path
import os


_base_dir = Path(__file__).resolve().parent
_comtypes_cache_dir = _base_dir / ".cache" / "comtypes"
_comtypes_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("COMTYPES_CACHE", str(_comtypes_cache_dir))

try:
    import comtypes.client
    import comtypes.gen

    comtypes.client.gen_dir = str(_comtypes_cache_dir)
    comtypes.gen.__path__ = [str(_comtypes_cache_dir)]
except Exception:
    pass
