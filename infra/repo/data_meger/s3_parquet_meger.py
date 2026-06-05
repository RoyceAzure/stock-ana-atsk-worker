import logging
from collections import Counter
from typing import Dict, List
import s3fs
from infra.repo.duckdb_manager import DuckDBManager

class S3ParquetMerger:
    """
        S3 資料合併工具。

        Attributes:
            base_path (str): S3 基礎路徑。
            duckdb_con: DuckDB 連線實例。

        Warns:
            ConcurrencyRisk: 本類別的 merge_single 方法非執行緒/進程安全。
            1. 臨時路徑衝突：多個實例同時處理同一個 code 會覆蓋 temp 檔案。
            2. 檔案遺失：一個實例在清理舊檔時，會導致另一個並行實例讀取失敗。
            
            建議：
            - 必須在外部實作分散式鎖（如 Redis Lock），確保同一個 code + candle 同時只有一個實例在跑。
            - 或使用單一排程器（Single Worker）依序處理。
        """
    def __init__(self, fs: s3fs.S3FileSystem, 
                 bucket_base_path: str):
        self.duckdb_con = DuckDBManager.get_conn()
        self.fs = fs
        self.base_path = bucket_base_path.replace("s3://", "").rstrip('/')
        self.logger = logging.getLogger(__name__)

    def clean_invalid_columns(self, invalid_columns: List[str]):
        invalid_set = set(invalid_columns)
        if not invalid_set:
            return

        all_files = self.fs.glob(f"{self.base_path}/**/*.parquet")

        with self.duckdb_con.cursor() as con:
            for obj_path in all_files:
                try:
                    # S3 上物件可能已被刪除，先檢查是否存在，避免 404
                    if not self.fs.exists(obj_path):
                        self.logger.info(f"Skip cleaning missing object {obj_path}")
                        continue

                    duck_path = f"s3://{obj_path}"
                    # 先用 LIMIT 0 取得 schema
                    df_schema = con.execute(
                        f"SELECT * FROM read_parquet('{duck_path}') LIMIT 0"
                    ).df()
                    existing_cols = set(df_schema.columns)
                    cols_to_drop = existing_cols & invalid_set
                    if not cols_to_drop:
                        continue

                    exclude_clause = ", ".join(cols_to_drop)
                    temp_obj_path = f"{obj_path}.tmp_clean"
                    temp_duck_path = f"s3://{temp_obj_path}"

                    copy_sql = f"""
                        COPY (
                            SELECT * EXCLUDE ({exclude_clause})
                            FROM read_parquet('{duck_path}')
                        ) TO '{temp_duck_path}'
                        (FORMAT PARQUET, CODEC 'SNAPPY')
                    """
                    con.execute(copy_sql)

                    if self.fs.exists(obj_path):
                        self.fs.rm(obj_path, recursive=False)
                    self.fs.move(temp_obj_path, obj_path)

                    self.logger.info(
                        f"Cleaned invalid columns {sorted(cols_to_drop)} from {obj_path}"
                    )
                except Exception as e:
                    msg = str(e)
                    # 如果是 404 / Not Found，視為檔案已不存在，僅記錄為 info
                    if "404" in msg or "Not Found" in msg:
                        self.logger.info(f"Skip cleaning {obj_path} (already removed / 404): {e}")
                    else:
                        self.logger.error(f"Error cleaning {obj_path}: {e}")

    def rename_columns(self, rename_map: Dict[str, str]):
        """
        將所有 parquet 檔案中的欄位做批次改名。
        rename_map: {old_name: new_name}
        """
        if not rename_map:
            return

        # 目標欄位 -> 對應的舊欄位們，用來處理「舊名、新名同時存在」的情況
        target_to_sources = {}
        for old, new in rename_map.items():
            target_to_sources.setdefault(new, set()).add(old)

        all_files = self.fs.glob(f"{self.base_path}/**/*.parquet")

        with self.duckdb_con.cursor() as con:
            for obj_path in all_files:
                try:
                    if not self.fs.exists(obj_path):
                        self.logger.info(f"Skip renaming on missing object {obj_path}")
                        continue

                    duck_path = f"s3://{obj_path}"
                    df_schema = con.execute(
                        f"SELECT * FROM read_parquet('{duck_path}') LIMIT 0"
                    ).df()
                    cols = list(df_schema.columns)

                    # 找出這個檔案實際會用到的 rename
                    effective_map = {
                        old: new for old, new in rename_map.items() if old in cols
                    }
                    if not effective_map:
                        continue

                    # 依原本欄位順序產生 SELECT 清單，該改名的加 AS new_name
                    select_parts = []
                    for col in cols:
                        quoted_col = f'"{col}"'
                        if col in effective_map:
                            new_col = effective_map[col]
                            quoted_new = f'"{new_col}"'
                            select_parts.append(f"{quoted_col} AS {quoted_new}")
                        else:
                            select_parts.append(quoted_col)

                    select_clause = ", ".join(select_parts)

                    temp_obj_path = f"{obj_path}.tmp_rename"
                    temp_duck_path = f"s3://{temp_obj_path}"

                    copy_sql = f"""
                        COPY (
                            SELECT {select_clause}
                            FROM read_parquet('{duck_path}')
                        ) TO '{temp_duck_path}'
                        (FORMAT PARQUET, CODEC 'SNAPPY')
                    """
                    con.execute(copy_sql)

                    if self.fs.exists(obj_path):
                        self.fs.rm(obj_path, recursive=False)
                    self.fs.move(temp_obj_path, obj_path)

                    self.logger.info(
                        f"Renamed columns {effective_map} in {obj_path}"
                    )
                except Exception as e:
                    msg = str(e)
                    if "404" in msg or "Not Found" in msg:
                        self.logger.info(f"Skip renaming {obj_path} (already removed / 404): {e}")
                    else:
                        self.logger.error(f"Error renaming {obj_path}: {e}")

    def merge_single(self, code: str, candle: str):
        self.logger.info(f"Merging {code} {candle}...")
        source_query = f"s3://{self.base_path}/{code}_{candle}_*/*.parquet"
        max_retries = 2  # 設定重試次數
        attempt = 0
        # 1. 取得日期範圍
        while attempt <= max_retries:
            with self.duckdb_con.cursor() as con:
                try:
                    df = con.execute(f"SELECT MIN(trade_time_date)::DATE as s, MAX(trade_time_date)::DATE as e FROM read_parquet('{source_query}')").df()
                    start_s, end_s = df['s'][0].strftime('%Y-%m-%d'), df['e'][0].strftime('%Y-%m-%d')
                    
                    # 2. 路徑設定
                    target_name = f"{code}_{candle}_{start_s}_{end_s}.parquet"
                    final_path, temp_path = f"{self.base_path}/{target_name}", f"{self.base_path}/TEMP_{target_name}"

                    # 3. 原子性操作：寫入臨時區 -> 重新命名 -> 清理舊檔
                    #    在這邊就先依 trade_time 去重與排序，確保合併後的檔案本身已經是乾淨資料
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
                        ) TO 's3://{temp_path}/part-00000.snappy.parquet'
                        (FORMAT PARQUET, CODEC 'SNAPPY')
                    """
                    con.execute(dedup_and_sorted_copy_sql)
                    with self.fs.open(f"s3://{temp_path}/_SUCCESS", 'wb') as f: 
                        pass
                    
                    if self.fs.exists(final_path): 
                        self.fs.rm(final_path, recursive=True)
                    self.fs.move(temp_path, final_path, recursive=True)
                    
                    # 清理碎片
                    for old in self.fs.glob(f"{self.base_path}/{code}_{candle}_*.parquet"):
                        if old.rstrip('/') != final_path.rstrip('/'): 
                            self.fs.rm(old, recursive=True)
                    self.logger.info(f"Merged {code} to {final_path}")
                    return
                except Exception as e:
                    error_msg = str(e).lower()
                    self.logger.error(f"Merge error: {error_msg}")
                    is_fatal = "invalidated" in error_msg or "internal error" in error_msg or "integer cast" in error_msg
                    if is_fatal and attempt < max_retries:
                        attempt += 1
                        DuckDBManager.return_and_delete(self.duckdb_con)
                        self.duckdb_con = DuckDBManager.get_conn()
                        continue
                    self.logger.error("merge failed after max retries, skip this merge")
                finally:
                    if self.fs.exists(temp_path): 
                        self.fs.rm(temp_path, recursive=True)
                    try:
                        self.logger.info("duck db shrink memory start")
                        con.execute("PRAGMA shrink_memory();")
                    except:
                        pass
                    self.logger.info("duck db shrink memory end")
        return None, "超過最大重試次數"

    def batch_merge(self, task_list: List[Dict[str, str]]):
        for task in task_list: self.merge_single(task['code'], task['candle'])


    def merge_all_available_data(self):
        """合併舊有 {code, candle} 資料。僅當同一組合出現超過一次時才執行合併。"""
        all_paths = self.fs.glob(f"{self.base_path}/**/*.parquet")
        task_counts: Counter = Counter()
        seen_datasets = set()  # 避免 parquet 目錄與其內 part-*.snappy.parquet 重複計算
        for path in all_paths:
            # 正規化為 dataset 路徑：排除 parquet 目錄底下的 snappy 分區檔
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
            {"code": code, "candle": candle}
            for (code, candle), count in task_counts.items()
            if count > 1
        ]

        if not task_list:
            self.logger.info("沒有需要合併的資料（所有 {code, candle} 組合皆為單一來源）")
            return

        self.logger.info(f"偵測到 {len(task_list)} 組 (code, candle) 有重複需合併...")
        return self.batch_merge(task_list)
