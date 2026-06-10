import json
import uuid
from typing import Any, Dict, List, Optional

import psycopg2.extensions


def build_task_event_row(
    *,
    task_id: Optional[uuid.UUID] = None,
    status: str = "pending",
    **overrides: Any,
) -> Dict[str, Any]:
    task_id = task_id or uuid.uuid4()
    row: Dict[str, Any] = {
        "id": str(task_id),
        "status": status,
        "tester_name": "pytest_tester",
        "tester_params": json.dumps({}),
        "data_provider_name": "sql_loader",
        "source_meta_data": json.dumps({"code": "2330", "candle": "d1"}),
        "tpsl_name": "",
        "tpsl_params": None,
        "saver_params": json.dumps({"saver_name": "local", "saver_base_path": "/tmp"}),
        "trigger_type": "manaual",
        "triggered_by": "pytest",  # 與 tests/integration/conftest.py 的清理條件一致
        "event_name": "preprocessing",
        "event_stage": "init",
        "used_process_pool": False,
        "is_notify": False,
    }
    row.update(overrides)
    return row


class TaskEventFactory:
    def __init__(self, conn: psycopg2.extensions.connection):
        self._conn = conn
        self._created_ids: List[uuid.UUID] = []

    def create(self, status: str = "pending", **overrides: Any) -> uuid.UUID:
        row = build_task_event_row(status=status, **overrides)
        task_id = uuid.UUID(row["id"])

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO task_event (
                    id, status, tester_name, tester_params, data_provider_name,
                    source_meta_data, tpsl_name, tpsl_params, saver_params,
                    trigger_type, triggered_by, event_name, event_stage,
                    used_process_pool, is_notify
                ) VALUES (
                    %(id)s, %(status)s, %(tester_name)s, %(tester_params)s::jsonb,
                    %(data_provider_name)s, %(source_meta_data)s::jsonb, %(tpsl_name)s,
                    %(tpsl_params)s, %(saver_params)s::jsonb, %(trigger_type)s,
                    %(triggered_by)s, %(event_name)s, %(event_stage)s,
                    %(used_process_pool)s, %(is_notify)s
                )
                """,
                row,
            )
        self._conn.commit()
        self._created_ids.append(task_id)
        return task_id

    def cleanup(self) -> None:
        if not self._created_ids:
            return

        ids = [str(task_id) for task_id in self._created_ids]
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM task_event WHERE id = ANY(%s::uuid[])",
                (ids,),
            )
            cur.execute(
                "SELECT COUNT(*) FROM task_event WHERE id = ANY(%s::uuid[])",
                (ids,),
            )
            remaining = cur.fetchone()[0]
        self._conn.commit()
        self._created_ids.clear()

        if remaining:
            raise RuntimeError(f"測試資料刪除失敗，仍有 {remaining} 筆 task_event 殘留")
