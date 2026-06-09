-- 恢復修改 (相同方法，逆向操作)
CREATE TYPE trigger_type_new AS ENUM ('manual', 'scheduler');

ALTER TABLE task_event 
    ALTER COLUMN trigger_type TYPE trigger_type_new 
    USING (CASE 
            WHEN trigger_type::text = 'manaual' THEN 'manual'::text::trigger_type_new
            WHEN trigger_type::text = 'scheduled' THEN 'scheduler'::text::trigger_type_new
            ELSE 'manual'::text::trigger_type_new
           END);

DROP TYPE trigger_type;
ALTER TYPE trigger_type_new RENAME TO trigger_type;