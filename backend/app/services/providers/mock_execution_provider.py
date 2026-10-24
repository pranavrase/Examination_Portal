import asyncio
from app.services.execution_provider import ExecutionProvider, ExecutionResultData


class MockExecutionProvider(ExecutionProvider):
    """
    Mock Execution Provider for testing and local development.
    Simulates various execution scenarios (Accepted, WA, TLE, MLE, CE, RE)
    without running code inside the backend server environment.
    """

    def __init__(self, default_status: str = "success"):
        self.default_status = default_status

    async def execute(
        self,
        source_code: str,
        language: str,
        stdin: str,
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 128000,
    ) -> ExecutionResultData:
        # Simulate slight async execution delay
        await asyncio.sleep(0.001)

        code_upper = source_code.upper()

        # 1. Compilation Error Simulation
        if "SIMULATE_CE" in code_upper or "SIMULATE_COMPILATION_ERROR" in code_upper:
            return ExecutionResultData(
                compile_output="error: expected ';' before '}' token",
                exit_code=1,
                execution_time_ms=0,
                memory_used_kb=0,
                status="compilation_error",
                error_message="Compilation failed",
            )

        # 2. Time Limit Exceeded Simulation
        if "SIMULATE_TLE" in code_upper or "SIMULATE_TIME_LIMIT" in code_upper:
            return ExecutionResultData(
                exit_code=124,
                execution_time_ms=time_limit_ms + 150,
                memory_used_kb=15000,
                status="time_limit_exceeded",
                error_message="Time limit exceeded",
            )

        # 3. Memory Limit Exceeded Simulation
        if "SIMULATE_MLE" in code_upper or "SIMULATE_MEMORY_LIMIT" in code_upper:
            return ExecutionResultData(
                exit_code=137,
                execution_time_ms=100,
                memory_used_kb=memory_limit_kb + 2048,
                status="memory_limit_exceeded",
                error_message="Memory limit exceeded",
            )

        # 4. Runtime Error Simulation
        if "SIMULATE_RE" in code_upper or "SIMULATE_RUNTIME_ERROR" in code_upper:
            return ExecutionResultData(
                stderr="ZeroDivisionError: division by zero",
                exit_code=1,
                execution_time_ms=45,
                memory_used_kb=18000,
                status="runtime_error",
                error_message="Runtime error occurred",
            )

        # 5. Wrong Answer Simulation
        if "SIMULATE_WA" in code_upper or "SIMULATE_WRONG_ANSWER" in code_upper:
            return ExecutionResultData(
                stdout="INCORRECT_OUTPUT_VALUE\n",
                exit_code=0,
                execution_time_ms=35,
                memory_used_kb=12000,
                status="success",
            )

        # 6. Basic Python / Algorithm simulation for common test cases
        clean_code = source_code.strip()
        stdin_clean = stdin.strip()

        # Sum of numbers
        if "sum(map(int, input().split()))" in clean_code:
            try:
                nums = list(map(int, stdin_clean.split()))
                out = f"{sum(nums)}\n"
            except Exception:
                out = f"{stdin_clean}\n"
            return ExecutionResultData(
                stdout=out,
                exit_code=0,
                execution_time_ms=25,
                memory_used_kb=12500,
                status="success",
            )

        # Reverse string
        if "[::-1]" in clean_code or "reverse" in clean_code.lower():
            return ExecutionResultData(
                stdout=f"{stdin_clean[::-1]}\n",
                exit_code=0,
                execution_time_ms=20,
                memory_used_kb=11000,
                status="success",
            )

        # Fallback simulation
        return ExecutionResultData(
            stdout=f"{stdin_clean}\n",
            exit_code=0,
            execution_time_ms=30,
            memory_used_kb=12000,
            status=self.default_status,
        )
