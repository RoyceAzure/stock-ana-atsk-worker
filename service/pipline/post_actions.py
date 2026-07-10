from typing import Callable, Optional

import pandas as pd

from infra.repo.data_meger.base import DataMerger
from technicals.pd_helper import distinct_code_candle_pairs


def make_batch_merge_action(
    merger: DataMerger,
) -> Callable[[pd.DataFrame], Optional[str]]:
    """建立 sink 後依 df 的 (code, candle) 呼叫 batch_merge 的 post action。"""

    def batch_merge_action(df: pd.DataFrame) -> Optional[str]:
        pairs = distinct_code_candle_pairs(df)
        if not pairs:
            return None
        try:
            merger.batch_merge(pairs)
        except Exception as e:
            return str(e)
        return None

    return batch_merge_action
