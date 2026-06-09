ALTER TABLE task_event 
DROP COLUMN IF EXISTS is_notify;

ALTER TABLE backtest_scheduler_task 
DROP COLUMN IF EXISTS is_notify;