from typing import Optional
from app.services.execution_provider import ExecutionProvider, ExecutionResultData
from app.services.judge0_service import Judge0Service


class Judge0ExecutionProvider(ExecutionProvider):
    """
    Judge0 Execution Provider implementing the ExecutionProvider interface.
    Sends code execution requests to Judge0 sandboxed execution engine.
    """

    def __init__(self, judge0_service: Optional[Judge0Service] = None):
        self.service = judge0_service or Judge0Service()

    async def execute(
        self,
        source_code: str,
        language: str,
        stdin: str,
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 128000,
    ) -> ExecutionResultData:
        return await self.service.execute_code(
            source_code=source_code,
            language=language,
            stdin=stdin,
            time_limit_ms=time_limit_ms,
            memory_limit_kb=memory_limit_kb,
        )
