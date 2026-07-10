import logging
import os
import platform
from typing import Any, Optional

import pandas as pd


def _get_process_rss_mb() -> Optional[float]:
    """Return process RSS in MB, best-effort on current OS."""
    system = platform.system().lower()
    try:
        if system == "windows":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            )
            if ok:
                return counters.WorkingSetSize / (1024 * 1024)
            return None

        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if system == "darwin":
            return rss / (1024 * 1024)
        return rss / 1024
    except Exception:
        return None


def _dataframe_mem_mb(df: Optional[pd.DataFrame]) -> Optional[float]:
    if df is None:
        return None
    try:
        return float(df.memory_usage(deep=True).sum() / (1024 * 1024))
    except Exception:
        return None


def log_mem(
    logger: logging.Logger,
    phase: str,
    df: Optional[pd.DataFrame] = None,
    **fields: Any,
) -> None:
    """Log memory snapshot with optional DataFrame footprint."""
    payload = {
        "phase": phase,
        "pid": os.getpid(),
        "rss_mb": _get_process_rss_mb(),
    }

    if df is not None:
        payload["df_shape"] = f"{df.shape[0]}x{df.shape[1]}"
        payload["df_mem_mb"] = _dataframe_mem_mb(df)

    payload.update(fields)
    msg = " ".join(f"{k}={v}" for k, v in payload.items())
    logger.info("[log_mem] %s", msg)
