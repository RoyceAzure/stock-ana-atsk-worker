-- 1. 刪除關聯明細表 (子表)
DROP TABLE IF EXISTS code_group_items;

DROP TRIGGER IF EXISTS update_user_code_groups_modtime ON user_code_groups;

-- 2. 刪除集合主表 (父表)
DROP TABLE IF EXISTS user_code_groups;