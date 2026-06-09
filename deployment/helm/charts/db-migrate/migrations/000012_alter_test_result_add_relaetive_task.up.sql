ALTER TABLE "test_result" 
  ADD COLUMN task_event_id UUID NOT NULL,
  ADD CONSTRAINT fk_task_event_id FOREIGN KEY (task_event_id) REFERENCES task_event(id);