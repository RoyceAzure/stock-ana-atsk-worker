CREATE TABLE "process_log" (
  "task_id" uuid PRIMARY KEY,
  "action" text NOT NULL,
  "module" text NOT NULL,
  "args" jsonb,
  "start_time" timestamp NOT NULL DEFAULT (now()),
  "end_time" timestamp NOT NULL,
  "duration" interval NOT NULL,
  "status" varchar(20) NOT NULL,
  "error" text,
  "result" jsonb
);

CREATE INDEX "idx_process_log_task_id"  ON "process_log" ("task_id");

CREATE INDEX "idx_process_log_status"  ON "process_log" ("status");

CREATE INDEX "idx_process_log_function_name" ON "process_log" ("action");

CREATE INDEX "idx_process_log_start_time_end_time"  ON "process_log" ("start_time", "end_time");