-- Drop all created indexes
DROP INDEX IF EXISTS "idx_task_event_triggered_by";
DROP INDEX IF EXISTS "idx_task_event_trigger_type";
DROP INDEX IF EXISTS "idx_task_event_created_at";
DROP INDEX IF EXISTS "idx_task_event_tester_name";
DROP INDEX IF EXISTS "idx_task_event_status";

-- Drop the main table
DROP TABLE IF EXISTS "task_event";

-- Drop the custom enum types
DROP TYPE IF EXISTS "trigger_type";
DROP TYPE IF EXISTS "task_status";