DROP TRIGGER IF EXISTS update_trade_price_modtime ON trade_price;

ALTER TABLE trade_price 
DROP COLUMN IF EXISTS updated_at,
DROP COLUMN IF EXISTS created_at;