from __future__ import annotations

from typing import Any
from crewai.tools import BaseTool

class SyncBaseTool(BaseTool):
    """
    CrewAI sometimes calls _arun from sync contexts (native tools loop),
    which can lead to 'coroutine was never awaited' warnings because BaseTool._arun is async.
    Override _arun as a sync function to guarantee non-coroutine execution.
    """

    def _arun(self, *args: Any, **kwargs: Any) -> Any:  # intentionally NOT async
        return self._run(*args, **kwargs)