CREATE TABLE IF NOT EXISTS user_code_groups (
    group_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL, -- 假設對應 Users.id
    alias VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- 建立複合唯一約束 (同時產生唯一索引)
    UNIQUE (user_id, alias)
);

DROP TRIGGER IF EXISTS trg_update_user_code_groups_modtime ON user_code_groups;
CREATE TRIGGER trg_update_user_code_groups_modtime
    BEFORE UPDATE ON user_code_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TABLE IF NOT EXISTS code_group_items (
    item_id SERIAL PRIMARY KEY,
    group_id INT NOT NULL,
    code VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- 建立外鍵約束，當主表刪除時自動清理
    CONSTRAINT fk_group
        FOREIGN KEY (group_id) 
        REFERENCES user_code_groups(group_id) 
        ON DELETE CASCADE,

    -- 建立複合唯一約束，防止同個群組內重複出現同個 code
    UNIQUE (group_id, code)
);
