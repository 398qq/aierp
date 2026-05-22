"""AI API router — backward compatibility shim.

All endpoints have been moved to submodules under app.api.v1.ai/.
This file re-exports the composed router for backward compatibility.
"""

from app.api.v1.ai import router

__all__ = ["router"]
