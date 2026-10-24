from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class ExecutionResultData(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    exit_code: Optional[int] = 0
    execution_time_ms: Optional[int] = 0
    memory_used_kb: Optional[int] = 0
    status: str = "success"  # "success", "runtime_error", "compilation_error", "time_limit_exceeded", "memory_limit_exceeded"
    error_message: Optional[str] = None


class ExecutionProvider(ABC):
    """
    Abstract Execution Provider interface for code execution.
    Module 2.6 uses this abstraction.
    Module 2.7 will provide the Judge0 implementation.
    """

    @abstractmethod
    async def execute(
        self,
        source_code: str,
        language: str,
        stdin: str,
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 128000,
    ) -> ExecutionResultData:
        """
        Execute source code against given stdin under resource constraints.
        """
        pass


def get_execution_provider(provider_type: Optional[str] = None) -> ExecutionProvider:
    """
    Factory function returning the configured ExecutionProvider.
    Defaults to Judge0ExecutionProvider if EXECUTION_PROVIDER == 'judge0'.
    Falls back to MockExecutionProvider only if explicitly configured as 'mock'.
    """
    from app.core.config import settings

    ptype = (provider_type or settings.EXECUTION_PROVIDER or "judge0").lower().strip()
    if ptype == "judge0":
        from app.services.providers.judge0_execution_provider import Judge0ExecutionProvider
        return Judge0ExecutionProvider()
    else:
        from app.services.providers.mock_execution_provider import MockExecutionProvider
        return MockExecutionProvider()

