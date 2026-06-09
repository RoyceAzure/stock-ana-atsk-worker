-- 1. 移除外鍵約束
ALTER TABLE user_code_groups
DROP CONSTRAINT IF EXISTS fk_user_code_groups_user_id;
