CREATE INDEX idx_test_result_name_code_combined 
ON test_result (
    (strategy_parms->>'name'),
    ((strategy_parms->'data_model')->>'code')
);