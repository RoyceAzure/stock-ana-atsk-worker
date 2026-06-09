ALTER TABLE trade_price 
ADD COLUMN IF NOT EXISTS created_at timestamp(6) DEFAULT timezone('utc', now()),
ADD COLUMN IF NOT EXISTS updated_at timestamp(6) DEFAULT timezone('utc', now());

DROP TRIGGER IF EXISTS update_trade_price_modtime ON trade_price;
CREATE TRIGGER update_trade_price_modtime
    BEFORE INSERT OR UPDATE ON trade_price
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();