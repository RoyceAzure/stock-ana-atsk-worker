ALTER TABLE trade_price ADD CONSTRAINT unique_trade_price UNIQUE (code, trade_time, candle);
