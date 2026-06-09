CREATE TYPE "candle_stick" AS ENUM (
  'd1'
);

CREATE TABLE IF NOT EXISTS "trade_price" (
  "id" BIGSERIAL PRIMARY KEY,
  "code" varchar(25) NOT NULL,
  "open" decimal(10,2) NOT NULL,
  "close" decimal(10,2) NOT NULL,
  "high" decimal(10,2) NOT NULL,
  "low" decimal(10,2) NOT NULL,
  "trade_time" timestamptz NOT NULL,
  "candle" candle_stick NOT NULL,
  "volume" bigint NOT NULL,
  "volume_weight" integer
);