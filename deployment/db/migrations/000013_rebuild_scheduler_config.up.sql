DROP TABLE IF EXISTS "backtest_scheduler_task";

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE "backtest_scheduler_task" (
    id varchar(100) NOT NULL DEFAULT 's_' || uuid_generate_v4(),
    cron_id int NOT NULL,
    nick_name text unique,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_user varchar(100) NOT NULL DEFAULT 'todo',
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_user varchar(100) NOT NULL DEFAULT 'todo',
    tester_name varchar(100) NOT NULL,
    tester_params jsonb NOT NULL,
    data_provider_name varchar(100) NOT NULL,
    code varchar(30) NOT NULL,
    candle candle_stick NOT NULL,
    tpsl_name varchar(100) NOT NULL,
    tpsl_params jsonb NOT NULL,
    saver_params jsonb NOT NULL,
    trigger_time varchar(50) NOT NULL,
    task_type varchar(30) NOT NULL DEFAULT 'invalid'::character varying,
    time_range varchar(10) NOT NULL DEFAULT 'm9'::character varying,
    PRIMARY KEY (id)
);

COMMENT ON COLUMN "backtest_scheduler_task".cron_id IS '對應的cron 內部排程任務 ID';