"""ARM Flash Programming Tool Version Information"""

import sys
from pathlib import Path

__version__ = "1.7.0"
__version_info__ = (1, 7, 0)
__author__ = "Aspiring-Freeman"
__email__ = ""
__license__ = "MIT"
__copyright__ = "Copyright 2026 Aspiring-Freeman"

VERSION = __version__


def get_pyocd_version() -> str:
    """Get vendored pyOCD version information
    
    Returns:
        Version string in format: "version (commit_id)"
        or "unknown" if not available
    """
    try:
        # Try to get pyOCD module path
        project_root = Path(__file__).parent
        pyocd_path = project_root / "Driver" / "pyOCD" / "pyocd"
        
        if not pyocd_path.exists():
            return "not installed (submodule missing)"
        
        # Try to import pyOCD and get version
        sys.path.insert(0, str(project_root / "Driver" / "pyOCD"))
        try:
            import pyocd
            version = getattr(pyocd, '__version__', 'unknown')
        except ImportError:
            version = "unknown"
        
        # Try to get git commit info
        import subprocess
        try:
            git_dir = project_root / "Driver" / "pyOCD"
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%h %ci'],
                cwd=str(git_dir),
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                commit_info = result.stdout.strip().split()[0]  # Get short hash
                return f"{version} (commit: {commit_info})"
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        return version
    except Exception as e:
        return f"error: {e}"
