-- 對於日期索引
CREATE INDEX IF NOT EXISTS idx_code_candle_trade_time ON trade_price (code, candle, date_trunc('day', (trade_time AT TIME ZONE 'UTC')));

-- 對於小時索引
CREATE INDEX IF NOT EXISTS idx_code_candle_trade_time_hour ON trade_price
(code, candle, date_trunc('hour', (trade_time AT TIME ZONE 'UTC')));

-- 對於分鐘索引
CREATE INDEX IF NOT EXISTS idx_code_candle_trade_time_minute ON trade_price
(code, candle, date_trunc('minute', (trade_time AT TIME ZONE 'UTC')));
