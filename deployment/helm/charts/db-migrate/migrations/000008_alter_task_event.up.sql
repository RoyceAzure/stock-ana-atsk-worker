ALTER TABLE "task_event" 
ADD COLUMN event_name varchar(100) NOT NULL DEFAULT 'none';

ALTER TABLE "task_event" 
ADD COLUMN event_stage varchar(100) NOT NULL DEFAULT 'none';