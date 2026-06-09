-- ==========================================
-- 1. 建立通訊錄表 (user_contacts)
-- ==========================================
CREATE TABLE "user_contacts" (
  "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  "user_id" INT NOT NULL,
  "type" VARCHAR(50) NOT NULL,    -- 例如: 'email', 'line'
  "target" VARCHAR(255) NOT NULL, -- 例如: 'test@gmail.com'
  "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
  "created_at" TIMESTAMP DEFAULT NOW(),
  "updated_at" TIMESTAMP DEFAULT NOW(),

  -- 建立外鍵關聯 (當 User 被刪除，通訊錄自動刪除)
  CONSTRAINT "fk_user_contacts_users" 
    FOREIGN KEY ("user_id") 
    REFERENCES "users" ("id") 
    ON DELETE CASCADE,

  -- 複合唯一索引 (避免重複建立相同的聯絡資料)
  CONSTRAINT "uq_user_contacts_unique_target" 
    UNIQUE ("user_id", "type", "target")
);

-- ==========================================
-- 2. 建立訂閱綁定表 (schedule_bindings)
-- ==========================================
CREATE TABLE "schedule_bindings" (
  "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  "user_id" INT NOT NULL,
  "schedule_id" VARCHAR(100) NOT NULL,
  "created_at" TIMESTAMP DEFAULT NOW(),
  "updated_at" TIMESTAMP DEFAULT NOW(),

  -- 建立外鍵關聯 (當 User 被刪除，訂閱自動刪除)
  CONSTRAINT "fk_schedule_bindings_users" 
    FOREIGN KEY ("user_id") 
    REFERENCES "users" ("id") 
    ON DELETE CASCADE,

  -- 建立外鍵關聯 (當排程任務被刪除，訂閱自動刪除)
  CONSTRAINT "fk_schedule_bindings_tasks" 
    FOREIGN KEY ("schedule_id") 
    REFERENCES "backtest_scheduler_task" ("id") 
    ON DELETE CASCADE,

  -- 複合唯一索引 (避免重複訂閱同一個排程)
  CONSTRAINT "uq_schedule_bindings_unique_sub" 
    UNIQUE ("user_id", "schedule_id")
);

-- ==========================================
-- 3. 設定自動更新 updated_at 的 Trigger
--    (PostgreSQL 需要這個步驟才能讓 updated_at 在修改時變更)
-- ==========================================

-- 建立共用的更新時間函數
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 綁定 Trigger 到 user_contacts 表
CREATE TRIGGER update_user_contacts_modtime
    BEFORE UPDATE ON "user_contacts"
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- 綁定 Trigger 到 schedule_bindings 表
CREATE TRIGGER update_schedule_bindings_modtime
    BEFORE UPDATE ON "schedule_bindings"
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();