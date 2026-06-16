import logging
from typing import Any, Dict, List

from infra.repo.duckdb.config import DuckDBStorageConfig, strip_uri_scheme
from infra.repo.duckdb_manager import DuckDBManager

logger = logging.getLogger(__name__)


class BlobParquetDataHelper:
    """物件儲存 Parquet 資料維護工具（schema 清理、欄位改名等）。"""

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

    def clean_invalid_columns(self, invalid_columns: List[str]):
        invalid_set = set(invalid_columns)
        if not invalid_set:
            return

        all_files = self.fs.glob(f"{self.base_path}/**/*.parquet")

        with self.duckdb_con.cursor() as con:
            for obj_path in all_files:
                try:
                    if not self.fs.exists(obj_path):
                        logger.info(f"Skip cleaning missing object {obj_path}")
                        continue

                    duck_path = self._duck_uri(obj_path)
                    df_schema = con.execute(
                        f"SELECT * FROM read_parquet('{duck_path}') LIMIT 0"
                    ).df()
                    existing_cols = set(df_schema.columns)
                    cols_to_drop = existing_cols & invalid_set
                    if not cols_to_drop:
                        continue

                    exclude_clause = ", ".join(cols_to_drop)
                    temp_obj_path = f"{obj_path}.tmp_clean"
                    temp_duck_path = self._duck_uri(temp_obj_path)

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

                    logger.info(
                        f"Cleaned invalid columns {sorted(cols_to_drop)} from {obj_path}"
                    )
                except Exception as e:
                    msg = str(e)
                    if "404" in msg or "Not Found" in msg:
                        logger.info(f"Skip cleaning {obj_path} (already removed / 404): {e}")
                    else:
                        logger.error(f"Error cleaning {obj_path}: {e}")

    def rename_columns(self, rename_map: Dict[str, str]):
        """將所有 parquet 檔案中的欄位做批次改名。rename_map: {old_name: new_name}"""
        if not rename_map:
            return

        all_files = self.fs.glob(f"{self.base_path}/**/*.parquet")

        with self.duckdb_con.cursor() as con:
            for obj_path in all_files:
                try:
                    if not self.fs.exists(obj_path):
                        logger.info(f"Skip renaming on missing object {obj_path}")
                        continue

                    duck_path = self._duck_uri(obj_path)
                    df_schema = con.execute(
                        f"SELECT * FROM read_parquet('{duck_path}') LIMIT 0"
                    ).df()
                    cols = list(df_schema.columns)

                    effective_map = {
                        old: new for old, new in rename_map.items() if old in cols
                    }
                    if not effective_map:
                        continue

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
                    temp_duck_path = self._duck_uri(temp_obj_path)

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

                    logger.info(
                        f"Renamed columns {effective_map} in {obj_path}"
                    )
                except Exception as e:
                    msg = str(e)
                    if "404" in msg or "Not Found" in msg:
                        logger.info(f"Skip renaming {obj_path} (already removed / 404): {e}")
                    else:
                        logger.error(f"Error renaming {obj_path}: {e}")
