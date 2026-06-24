import logging
from collections import Counter
from typing import Any, List, Tuple

import duckdb

from infra.repo.duckdb.config import DuckDBStorageConfig, strip_uri_scheme
from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.duckdb_manager import DuckDBManager

logger = logging.getLogger(__name__)

_MAX_MERGE_RETRIES = 2
_RETRIABLE_MERGE_ERROR_KEYWORDS = (
    "invalidated",
    "internal error",
    "integer cast",
)


def _is_retriable_merge_error(exc: Exception) -> bool:
    if isinstance(exc, duckdb.Error):
        msg = str(exc).lower()
        return any(keyword in msg for keyword in _RETRIABLE_MERGE_ERROR_KEYWORDS)
    msg = str(exc).lower()
    return any(keyword in msg for keyword in _RETRIABLE_MERGE_ERROR_KEYWORDS)


class BlobParquetMerger:
    """
        物件儲存 Parquet 合併工具（支援 S3 / MinIO / GCS）。

        Attributes:
            base_path (str): bucket 內基礎路徑（不含 scheme）。
            duckdb_con: DuckDB 連線實例。

        Warns:
            ConcurrencyRisk: 本類別的 merge_single 方法非執行緒/進程安全。
            1. 臨時路徑衝突：多個實例同時處理同一個 code 會覆蓋 temp 檔案。
            2. 檔案遺失：一個實例在清理舊檔時，會導致另一個並行實例讀取失敗。

            建議：
            - 必須在外部實作分散式鎖（如 Redis Lock），確保同一個 code + candle 同時只有一個實例在跑。
            - 或使用單一排程器（Single Worker）依序處理。
        """

    def __init__(
        self,
        fs: Any,
        bucket_base_path: str,
        duckdb_config: DuckDBStorageConfig,
    ):
        self.duckdb_con = DuckDBManager.get_conn()
        self.fs = fs
        self.duckdb_config = duckdb_config
        self.base_path = strip_uri_scheme(bucket_base_path)

    def _duck_uri(self, path: str) -> str:
        return self.duckdb_config.to_uri(path)

    def _fs_uri(self, path: str) -> str:
        return self._duck_uri(path)

    def _normalize_dataset_folder(self, path: str) -> str:
        """將 part 檔或 URI 正規化為 dataset 資料夾路徑（bucket/xxx.parquet）。"""
        folder = strip_uri_scheme(path).rstrip("/")
        if "/part-" in folder:
            folder = folder.split("/part-")[0]
        return folder

    def _dataset_glob_prefix(self, code: str, candle: str) -> str:
        return f"{self.base_path}/{code}_{candle}_*"

    def _list_merge_sources(self, code: str, candle: str) -> List[str]:
        return self.fs.glob(f"{self._dataset_glob_prefix(code, candle)}/part-*.parquet")

    def _list_dataset_folders(self, code: str, candle: str) -> List[str]:
        folders = {
            self._normalize_dataset_folder(path)
            for path in self._list_merge_sources(code, candle)
        }
        return sorted(folders)

    def _remove_dataset_folder(self, folder_path: str) -> None:
        folder = self._normalize_dataset_folder(folder_path)
        if self.fs.exists(folder):
            self.fs.rm(folder, recursive=True)

    def _move_dataset_folder(self, src_folder: str, dst_folder: str) -> None:
        """將虛擬 dataset 資料夾（*.parquet/ 下的 part、_SUCCESS）搬到目標路徑。

        s3fs 的 recursive move 在資料夾名稱以 .parquet 結尾時會誤當單一物件而失敗，
        改以 glob + cp + rm 逐檔搬移。
        """
        src = self._normalize_dataset_folder(src_folder)
        dst = self._normalize_dataset_folder(dst_folder)
        children = self.fs.glob(f"{src}/*")
        if not children:
            raise FileNotFoundError(f"dataset folder is empty or missing: {src}")
        for path in children:
            name = path.rsplit("/", 1)[-1]
            self.fs.cp(path, f"{dst}/{name}")
        self.fs.rm(src, recursive=True)

    def _cleanup_old_datasets(
        self, code: str, candle: str, keep_folder: str
    ) -> None:
        keep = self._normalize_dataset_folder(keep_folder)
        for folder in self._list_dataset_folders(code, candle):
            if folder != keep:
                logger.info("Removing old dataset folder: %s", folder)
                self._remove_dataset_folder(folder)

    def merge_single(self, code: str, candle: str) -> None:
        sources = self._list_merge_sources(code, candle)
        if not sources:
            logger.info(
                "No source parquet for merge, skip: code=%s candle=%s",
                code,
                candle,
            )
            return

        source_query = self._duck_uri(
            f"{self.base_path}/{code}_{candle}_*/part-*.parquet"
        )

        for attempt in range(_MAX_MERGE_RETRIES + 1):
            temp_path = ""
            moved = False
            logger.info(
                "Merging code=%s candle=%s attempt=%s source_count=%s",
                code,
                candle,
                attempt,
                len(sources),
            )
            with self.duckdb_con.cursor() as con:
                try:
                    df = con.execute(
                        f"SELECT MIN(trade_time_date)::DATE as s, MAX(trade_time_date)::DATE as e "
                        f"FROM read_parquet('{source_query}')"
                    ).df()
                    start_s, end_s = (
                        df["s"][0].strftime("%Y-%m-%d"),
                        df["e"][0].strftime("%Y-%m-%d"),
                    )

                    target_name = f"{code}_{candle}_{start_s}_{end_s}.parquet"
                    final_path = f"{self.base_path}/{target_name}"
                    temp_path = f"{self.base_path}/TEMP_{target_name}"

                    dedup_and_sorted_copy_sql = f"""
                        COPY (
                            SELECT * EXCLUDE (rn)
                            FROM (
                                SELECT
                                    *,
                                    ROW_NUMBER() OVER (PARTITION BY trade_time ORDER BY trade_time) AS rn
                                FROM read_parquet('{source_query}')
                            )
                            WHERE rn = 1
                            ORDER BY trade_time
                        ) TO '{self._duck_uri(f"{temp_path}/part-00000.snappy.parquet")}'
                        (FORMAT PARQUET, CODEC 'SNAPPY')
                    """
                    con.execute(dedup_and_sorted_copy_sql)
                    success_uri = self._duck_uri(f"{temp_path}/_SUCCESS")
                    if isinstance(self.duckdb_config, GcsDuckDBConfig):
                        con.execute(
                            f"COPY (SELECT 1) TO '{success_uri}' "
                            f"(FORMAT CSV, HEADER false)"
                        )
                    else:
                        with self.fs.open(success_uri, "wb"):
                            pass

                    self._remove_dataset_folder(final_path)
                    self._move_dataset_folder(temp_path, final_path)
                    moved = True
                    self._cleanup_old_datasets(code, candle, final_path)
                    logger.info(
                        "Merged code=%s candle=%s to %s",
                        code,
                        candle,
                        final_path,
                    )
                    return
                except Exception as e:
                    can_retry = _is_retriable_merge_error(e) and attempt < _MAX_MERGE_RETRIES
                    logger.error(
                        "Merge error code=%s candle=%s attempt=%s retriable=%s: %s",
                        code,
                        candle,
                        attempt,
                        can_retry,
                        e,
                    )
                    if can_retry:
                        DuckDBManager.return_and_delete(self.duckdb_con)
                        self.duckdb_con = DuckDBManager.get_conn()
                        continue
                    logger.error(
                        "Merge failed, skip: code=%s candle=%s",
                        code,
                        candle,
                        exc_info=True,
                    )
                    return
                finally:
                    if temp_path and not moved and self.fs.exists(temp_path):
                        self.fs.rm(temp_path, recursive=True)
                    try:
                        con.execute("PRAGMA shrink_memory();")
                    except Exception:
                        pass
    def batch_merge(self, task_list: List[Tuple[str, str]]):
        for code, candle in task_list:
            self.merge_single(code, candle)

    def merge_all_available_data(self):
        """合併舊有 {code, candle} 資料。僅當同一組合出現超過一次時才執行合併。"""
        all_paths = self.fs.glob(f"{self.base_path}/**/*.parquet")
        task_counts: Counter = Counter()
        seen_datasets = set()
        for path in all_paths:
            if "/part-" in path:
                path = path.split("/part-")[0]
            if path in seen_datasets:
                continue
            seen_datasets.add(path)

            rel = path[len(self.base_path) :].lstrip("/")
            first_segment = rel.split("/")[0].replace(".parquet", "")
            parts = first_segment.split("_")
            if len(parts) >= 2:
                task_counts[(parts[0], parts[1])] += 1

        task_list = [
            (code, candle)
            for (code, candle), count in task_counts.items()
            if count > 1
        ]

        if not task_list:
            logger.info("沒有需要合併的資料（所有 {code, candle} 組合皆為單一來源）")
            return

        logger.info(f"偵測到 {len(task_list)} 組 (code, candle) 有重複需合併...")
        return self.batch_merge(task_list)
