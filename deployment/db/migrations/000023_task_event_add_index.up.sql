CREATE INDEX idx_task_event_main ON task_event((source_meta_data->>'code'), tester_name, event_name);

-- 時間查詢
CREATE INDEX idx_task_event_start_time ON task_event(start_time);
CREATE INDEX idx_task_event_end_time ON task_event(end_time);


CREATE INDEX idx_task_event_candle ON task_event((source_meta_data->>'candle'));