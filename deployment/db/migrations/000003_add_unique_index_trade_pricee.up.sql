
-- 查詢時必須要給code candle
CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_price_code_candle_time 
ON trade_price (code, candle, trade_time)
WHERE code IS NOT NULL AND candle IS NOT NULL;