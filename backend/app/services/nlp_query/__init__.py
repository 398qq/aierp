"""Natural-language ERP query — public API.

Public surface:
- :func:`natural_language_query` — the only function callers should use.

Internally:
- :mod:`.detection` — domain keyword classification
- :mod:`.context`   — per-domain SQL context builders
- :mod:`.service`   — orchestration (select contexts, call LLM)
"""

from .service import natural_language_query

__all__ = ["natural_language_query"]
