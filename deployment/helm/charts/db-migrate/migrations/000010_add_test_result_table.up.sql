CREATE TABLE "test_result" (
  "id" SERIAL PRIMARY KEY, -- 自動遞增的主鍵，用於唯一識別每一筆回測結果
  "key_string" varchar(255) UNIQUE NOT NULL,
  "strategy_parms" jsonb NOT NULL,
  "tester_params" jsonb NOT NULL,
  "summary" jsonb NOT NULL,
  "file" jsonb NOT NULL,
  "completed_at" timestamptz NOT NULL,
  "created_at" timestamptz NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz NOT NULL
);

CREATE INDEX "idx_test_result_strategy_parms" ON "test_result" USING GIN ("strategy_parms");

CREATE INDEX "idx_test_result_summary" ON "test_result" USING GIN ("summary");

CREATE INDEX "idx_test_result_completed_at" ON "test_result" ("completed_at");