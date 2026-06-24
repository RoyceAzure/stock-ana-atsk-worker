INSERT INTO task_event (
    id,
    status,
    tester_name,
    tester_params,
    data_provider_name,
    source_meta_data,
    tpsl_name,
    tpsl_params,
    saver_params,
    trigger_type,
    triggered_by,
    event_name,
    event_stage,
    used_process_pool,
    is_notify
) VALUES (
    '661f9511-f39c-42a5-b712-557766551111',
    'pending',
    'local_test',
    '{}'::jsonb,
    'sql_loader',
    '{"code": "[2330, 2317,7610,2408]", "candle": "d1", "start_time": "2025-01-01", "end_time": "2025-12-31"}'::jsonb,
    '',
    NULL,
    '{"saver_name": "gcs", "saver_base_path": "sexy_stock_test"}'::jsonb,
    'manaual',
    'local-dev',
    'preprocessing',
    'init',
    false,
    false
)
ON CONFLICT (id) DO UPDATE SET
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP,
    event_name = EXCLUDED.event_name,
    event_stage = EXCLUDED.event_stage,
    source_meta_data = EXCLUDED.source_meta_data,
    saver_params = EXCLUDED.saver_params;

SELECT id, status, event_name, event_stage, source_meta_data
FROM task_event
WHERE id = '661f9511-f39c-42a5-b712-557766551111';
