import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with open(root / "all_company.json", encoding="utf-8") as f:
    companies = json.load(f)

codes = [int(c["公司代號"]) for c in companies]
num_groups = 20
chunk_size = (len(codes) + num_groups - 1) // num_groups
groups = [codes[i : i + chunk_size] for i in range(0, len(codes), chunk_size)]
while len(groups) > num_groups:
    groups[-2].extend(groups[-1])
    groups.pop()


def code_json(group_codes: list[int]) -> str:
    return "[" + ", ".join(str(c) for c in group_codes) + "]"


lines = [
    "-- Seed task_event rows for all listed companies (~20 batches, triggered_by=test).",
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
    ]
)

out = root / "script" / "seed_test_task_event_all_companies.sql"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"written {out} ({len(codes)} codes, {len(groups)} batches)")
