-- 1. 新增外鍵約束
ALTER TABLE user_code_groups
ADD CONSTRAINT fk_user_code_groups_user_id
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;
