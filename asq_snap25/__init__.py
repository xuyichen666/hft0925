"""ASQ market making driven by frozen snap25 LightGBM fair mid.

Separate from `asq_tick` (online TOB LGBM). Optimize here, then push to
GitHub and run on the Tokyo server.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
