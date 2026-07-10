from typing import Callable, Optional
import logging

import pandas as pd

from infra.repo.data_meger.base import DataMerger
from technicals.pd_helper import distinct_code_candle_pairs
from util.memory_log import log_mem

logger = logging.getLogger(__name__)


def make_batch_merge_action(
    merger: DataMerger,
) -> Callable[[pd.DataFrame], Optional[str]]:
    """建立 sink 後依 df 的 (code, candle) 呼叫 batch_merge 的 post action。"""

    def batch_merge_action(df: pd.DataFrame) -> Optional[str]:
        pairs = distinct_code_candle_pairs(df)
        if not pairs:
            return None
        log_mem(
            logger,
            "merge_batch_start",
            df,
            pair_count=len(pairs),
        )
        try:
            merger.batch_merge(pairs)
        except Exception as e:
            log_mem(
                logger,
                "merge_batch_end",
                df,
                pair_count=len(pairs),
                err=str(e),
            )
            return str(e)
        log_mem(
            logger,
            "merge_batch_end",
            df,
            pair_count=len(pairs),
            err=None,
        )
        return None

    return batch_merge_action
