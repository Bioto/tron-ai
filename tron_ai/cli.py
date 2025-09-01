"""
Backward compatibility CLI entry point.

This module maintains the original CLI interface for backward compatibility
while delegating to the new modular CLI structure.
"""

import warnings
from tron_ai.cli.main import main

# Suppress warnings for cleaner output  
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb")

# Re-export main for backward compatibility
__all__ = ["main"]

if __name__ == "__main__":
    main()
