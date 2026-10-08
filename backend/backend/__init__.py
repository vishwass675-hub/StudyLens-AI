"""Compatibility package for Render services rooted at ``backend/``.

The existing Render service imports ``backend.main`` while its working
directory is already this backend directory. Extend this package's search
path so ``backend.app`` resolves to the application package beside this file.
"""

from pathlib import Path

__path__.append(str(Path(__file__).resolve().parent.parent))
