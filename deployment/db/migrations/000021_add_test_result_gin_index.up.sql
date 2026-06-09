CREATE INDEX idx_test_result_name 
ON test_result ((strategy_parms->>'name'));

CREATE INDEX idx_test_result_code 
ON test_result (((strategy_parms->'data_model')->>'code'));

CREATE INDEX idx_test_result_candle 
ON test_result (((strategy_parms->'data_model')->>'candle'));