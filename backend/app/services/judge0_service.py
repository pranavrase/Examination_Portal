import asyncio
import base64
import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.services.execution_provider import ExecutionResultData

logger = logging.getLogger(__name__)

# Centralized Language Mapping to Judge0 Language IDs
# Verified against ce.judge0.com languages API
LANGUAGE_MAP: Dict[str, int] = {
    "python": 71,       # Python (3.8.1)
    "python3": 71,
    "py": 71,
    "cpp": 54,          # C++ (GCC 9.2.0)
    "c++": 54,
    "c_cpp": 54,
    "cpp17": 54,
    "c": 50,            # C (GCC 9.2.0)
    "gcc": 50,
    "java": 62,         # Java (OpenJDK 13.0.1)
    "javascript": 63,   # JavaScript (Node.js 12.14.0)
    "js": 63,
    "node": 63,
}

# User-facing language names
LANGUAGE_NAMES: Dict[str, str] = {
    "python": "Python 3",
    "cpp": "C++ (GCC)",
    "c": "C (GCC)",
    "java": "Java (OpenJDK)",
    "javascript": "JavaScript (Node.js)",
}


def get_judge0_language_id(language: str) -> Optional[int]:
    """Map application language string to Judge0 language ID."""
    if not language:
        return None
    return LANGUAGE_MAP.get(language.strip().lower())


def _b64_encode(text: Optional[str]) -> Optional[str]:
    """Base64 encode a string for safe Judge0 payload transfer."""
    if text is None:
        return None
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _b64_decode(encoded: Optional[str]) -> Optional[str]:
    """Base64 decode a Judge0 response string."""
    if encoded is None:
        return None
    try:
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8", errors="replace")
    except Exception:
        return encoded


class Judge0Service:
    """
    Dedicated Judge0 Integration Service.
    Handles communication with Judge0 REST API:
    - Language mapping
    - Submissions with base64 encoding
    - Polling and status resolution
    - Resource limit enforcement
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        poll_interval: Optional[float] = None,
        max_poll_attempts: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.JUDGE0_BASE_URL or "https://ce.judge0.com").rstrip("/")
        self.api_key = api_key or settings.JUDGE0_API_KEY
        self.timeout_seconds = timeout_seconds or settings.JUDGE0_TIMEOUT_SECONDS
        self.poll_interval = poll_interval or settings.JUDGE0_POLL_INTERVAL_SECONDS
        self.max_poll_attempts = max_poll_attempts or settings.JUDGE0_MAX_POLL_ATTEMPTS

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ExamPortal-Judge0/1.0",
        }
        if self.api_key:
            if settings.JUDGE0_RAPIDAPI_HOST or "rapidapi.com" in self.base_url:
                headers["X-RapidAPI-Key"] = self.api_key
                headers["X-RapidAPI-Host"] = settings.JUDGE0_RAPIDAPI_HOST or "judge0-ce.p.rapidapi.com"
            else:
                headers["X-Auth-Token"] = self.api_key
        return headers

    async def execute_code(
        self,
        source_code: str,
        language: str,
        stdin: str = "",
        time_limit_ms: int = 2000,
        memory_limit_kb: int = 128000,
    ) -> ExecutionResultData:
        """
        Submit code to Judge0 and wait/poll for execution results.
        Returns normalized ExecutionResultData.
        """
        language_id = get_judge0_language_id(language)
        if not language_id:
            return ExecutionResultData(
                status="compilation_error",
                error_message=f"Unsupported language '{language}'. Supported languages: {list(LANGUAGE_NAMES.keys())}",
                exit_code=1,
            )

        # Convert limits for Judge0
        # cpu_time_limit in seconds (float allowed in Judge0 CE)
        cpu_time_limit = max(0.5, round(time_limit_ms / 1000.0, 2))
        # memory_limit in KB (Judge0 uses KB)
        memory_limit = max(16384, memory_limit_kb)

        payload = {
            "source_code": _b64_encode(source_code),
            "language_id": language_id,
            "stdin": _b64_encode(stdin),
            "cpu_time_limit": cpu_time_limit,
            "memory_limit": memory_limit,
        }

        url = f"{self.base_url}/submissions?base64_encoded=true&wait=true"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
                
                if resp.status_code not in (200, 201):
                    logger.error(f"Judge0 submission returned error HTTP {resp.status_code}: {resp.text}")
                    return ExecutionResultData(
                        status="runtime_error",
                        error_message=f"Code execution service returned HTTP {resp.status_code}. Please try again later.",
                        exit_code=1,
                    )

                data = resp.json()
                token = data.get("token")
                status_obj = data.get("status", {})
                status_id = status_obj.get("id")

                # If execution hasn't finished synchronously (status_id in [1, 2] = In Queue / Processing)
                if status_id in (1, 2) and token:
                    data = await self._poll_submission(client, token, headers)

                return self._parse_judge0_response(data, memory_limit_kb=memory_limit)

        except httpx.TimeoutException:
            logger.warning(f"Judge0 execution timed out after {self.timeout_seconds}s")
            return ExecutionResultData(
                status="time_limit_exceeded",
                error_message=f"Execution timed out ({self.timeout_seconds}s limit exceeded).",
                execution_time_ms=time_limit_ms,
                exit_code=124,
            )
        except httpx.RequestError as exc:
            logger.error(f"Network error connecting to Judge0 at {self.base_url}: {exc}")
            return ExecutionResultData(
                status="runtime_error",
                error_message="Code execution service is temporarily unreachable. Please contact the administrator.",
                exit_code=1,
            )
        except Exception as exc:
            logger.exception("Unexpected error in Judge0Service")
            return ExecutionResultData(
                status="runtime_error",
                error_message=f"Execution error: {str(exc)}",
                exit_code=1,
            )

    async def _poll_submission(
        self,
        client: httpx.AsyncClient,
        token: str,
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Poll Judge0 submission status until complete or max attempts reached."""
        poll_url = f"{self.base_url}/submissions/{token}?base64_encoded=true"
        for attempt in range(self.max_poll_attempts):
            await asyncio.sleep(self.poll_interval)
            try:
                resp = await client.get(poll_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status_id = data.get("status", {}).get("id")
                    if status_id not in (1, 2):  # Finished
                        return data
            except Exception as exc:
                logger.warning(f"Error polling Judge0 token {token} on attempt {attempt+1}: {exc}")

        # If still not finished after max attempts:
        return {
            "status": {"id": 5, "description": "Time Limit Exceeded"},
            "time": str(self.timeout_seconds),
            "message": "Submission timed out while queued or processing.",
        }

    def _parse_judge0_response(self, data: Dict[str, Any], memory_limit_kb: int = 0) -> ExecutionResultData:
        """Parse and normalize Judge0 response into ExecutionResultData."""
        status_obj = data.get("status", {})
        status_id = status_obj.get("id", 0)
        status_desc = status_obj.get("description", "")

        raw_stdout = _b64_decode(data.get("stdout"))
        raw_stderr = _b64_decode(data.get("stderr"))
        raw_compile = _b64_decode(data.get("compile_output"))
        message = data.get("message")

        # Time in ms
        time_sec = float(data.get("time") or 0.0)
        time_ms = int(time_sec * 1000)

        # Memory in KB
        memory_kb = int(data.get("memory") or 0)

        exit_code = data.get("exit_code") or 0

        # Determine normalized status:
        # Status IDs:
        # 3: Accepted
        # 4: Wrong Answer (if Judge0 ran its own comparison)
        # 5: Time Limit Exceeded
        # 6: Compilation Error
        # 7-12: Runtime Error (SIGSEGV, SIGXFSZ, SIGFPE, SIGABRT, NZEC, Other)
        # 13: Internal Error
        # 14: Exec Format Error
        is_syntax_error = bool(raw_stderr and "syntaxerror" in raw_stderr.lower())
        is_memory_error = bool(
            "memory" in status_desc.lower()
            or (raw_stderr and any(m in raw_stderr.lower() for m in ("memoryerror", "bad_alloc", "out of memory", "killed")))
            or (memory_limit_kb and memory_kb >= memory_limit_kb)
            or exit_code == 137
        )
        if status_id == 3:
            norm_status = "success"
        elif status_id == 4:
            norm_status = "wrong_answer"
        elif status_id == 5 or "time limit" in status_desc.lower():
            norm_status = "time_limit_exceeded"
        elif status_id == 6 or raw_compile or is_syntax_error:
            norm_status = "compilation_error"
        elif is_memory_error:
            norm_status = "memory_limit_exceeded"
        elif status_id in (7, 8, 9, 10, 11, 12, 14) or raw_stderr:
            norm_status = "runtime_error"
        elif status_id == 13:
            norm_status = "runtime_error"
        else:
            norm_status = "success" if (exit_code == 0 and not raw_stderr) else "runtime_error"

        error_message = None
        if norm_status == "compilation_error":
            error_message = raw_compile or (raw_stderr if is_syntax_error else None) or status_desc or "Compilation failed"
        elif norm_status == "runtime_error":
            error_message = raw_stderr or message or status_desc or "Runtime error occurred"
        elif norm_status == "time_limit_exceeded":
            error_message = message or status_desc or "Time limit exceeded"
        elif norm_status == "memory_limit_exceeded":
            error_message = message or status_desc or "Memory limit exceeded"

        return ExecutionResultData(
            stdout=raw_stdout,
            stderr=raw_stderr,
            compile_output=raw_compile,
            exit_code=exit_code,
            execution_time_ms=time_ms,
            memory_used_kb=memory_kb,
            status=norm_status,
            error_message=error_message,
        )
