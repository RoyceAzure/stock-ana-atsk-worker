-- 創建新的正確拼寫的 ENUM 類型
CREATE TYPE trigger_type_new AS ENUM ('manaual', 'scheduled');

-- 轉換現有數據到新類型
ALTER TABLE task_event 
    ALTER COLUMN trigger_type TYPE trigger_type_new 
    USING (CASE 
             WHEN trigger_type::text = 'manaual' THEN 'manaual'::text::trigger_type_new
             WHEN trigger_type::text = 'scheduler' THEN 'scheduled'::text::trigger_type_new
           END);

-- 刪除舊類型並重命名新類型
DROP TYPE trigger_type;
ALTER TYPE trigger_type_new RENAME TO trigger_type;