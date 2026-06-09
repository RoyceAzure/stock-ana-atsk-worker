DROP INDEX IF EXISTS "process_log".idx_process_log_task_id;
DROP INDEX IF EXISTS "process_log".idx_process_log_status;
DROP INDEX IF EXISTS "process_log".idx_process_log_function_name;
DROP INDEX IF EXISTS "process_log".idx_process_log_start_time_end_time;

DROP TABLE IF EXISTS "process_log"