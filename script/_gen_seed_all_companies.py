"""從 all_company.json 產生 seed_test_task_event_all_companies.sql。

用法:
  python script/_gen_seed_all_companies.py                  # 預設每筆 55 碼（約 20 批）
  python script/_gen_seed_all_companies.py --codes-per-task 10
  python script/_gen_seed_all_companies.py -n 1             # 一碼一任務
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate seed SQL: split all company codes into task_event batches.",
    )
    parser.add_argument(
        "-n",
        "--codes-per-task",
        type=int,
        default=55,
        metavar="N",
        help="每筆 task_event 包含的公司代號數量（最後一筆可能較少）。預設 55。",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="輸出 SQL 路徑（預設 script/seed_test_task_event_all_companies.sql）",
    )
    return parser.parse_args()


def chunk_codes(codes: list[int], codes_per_task: int) -> list[list[int]]:
    if codes_per_task < 1:
        raise ValueError("--codes-per-task 必須 >= 1")
    return [codes[i : i + codes_per_task] for i in range(0, len(codes), codes_per_task)]


def code_json(group_codes: list[int]) -> str:
    return "[" + ", ".join(str(c) for c in group_codes) + "]"


def build_sql(groups: list[list[int]], codes_per_task: int, total_codes: int) -> str:
    lines = [
        f"-- Seed task_event for all listed companies "
        f"(codes_per_task={codes_per_task}, batches={len(groups)}, total_codes={total_codes}).",
        "-- Regenerate: python script/_gen_seed_all_companies.py -n <codes_per_task>",
        "-- Cleanup: DELETE FROM task_event WHERE triggered_by = 'test';",
        "",
        "BEGIN;",
        "",
    ]

    for i, group in enumerate(groups, 1):
        uid = f"662f9522-f39c-42a5-b712-55776655{i:04d}"
        meta = (
            '{"code": "'
            + code_json(group)
            + '", "candle": "d1", "start_time": "2025-01-01", "end_time": "2025-12-31"}'
        )
        lines.extend(
            [
                f"-- Batch {i:02d}: {len(group)} codes",
                "INSERT INTO task_event (",
                "    id,",
                "    status,",
                "    tester_name,",
                "    tester_params,",
                "    data_provider_name,",
                "    source_meta_data,",
                "    tpsl_name,",
                "    tpsl_params,",
                "    saver_params,",
                "    trigger_type,",
                "    triggered_by,",
                "    event_name,",
                "    event_stage,",
                "    used_process_pool,",
                "    is_notify",
                ") VALUES (",
                f"    '{uid}',",
                "    'pending',",
                "    'local_test',",
                "    '{}'::jsonb,",
                "    'sql_loader',",
                f"    '{meta}'::jsonb,",
                "    '',",
                "    NULL,",
                "    '{\"saver_name\": \"gcs\", \"saver_base_path\": \"sexy_stock_test\"}'::jsonb,",
                "    'manaual',",
                "    'test',",
                "    'preprocessing',",
                "    'init',",
                "    false,",
                "    false",
                ")",
                "ON CONFLICT (id) DO UPDATE SET",
                "    status = EXCLUDED.status,",
                "    updated_at = CURRENT_TIMESTAMP,",
                "    event_name = EXCLUDED.event_name,",
                "    event_stage = EXCLUDED.event_stage,",
                "    source_meta_data = EXCLUDED.source_meta_data,",
                "    saver_params = EXCLUDED.saver_params,",
                "    triggered_by = EXCLUDED.triggered_by;",
                "",
            ]
        )

    lines.extend(
        [
            "COMMIT;",
            "",
            "SELECT",
            "    id,",
            "    status,",
            "    event_name,",
            "    triggered_by,",
            "    source_meta_data->>'code' AS code_list",
            "FROM task_event",
            "WHERE triggered_by = 'test'",
            "ORDER BY id;",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    with open(root / "all_company.json", encoding="utf-8") as f:
        companies = json.load(f)

    codes = [int(c["公司代號"]) for c in companies]
    groups = chunk_codes(codes, args.codes_per_task)
    out = args.output or (root / "script" / "seed_test_task_event_all_companies.sql")
    out.write_text(build_sql(groups, args.codes_per_task, len(codes)), encoding="utf-8")

    sizes = [len(g) for g in groups]
    print(
        f"written {out}\n"
        f"  total_codes={len(codes)}  codes_per_task={args.codes_per_task}  "
        f"batches={len(groups)}  "
        f"batch_sizes={min(sizes)}..{max(sizes)}"
    )


if __name__ == "__main__":
    main()
