DROP TRIGGER IF EXISTS update_schedule_bindings_modtime ON schedule_bindings;
CREATE TRIGGER update_schedule_bindings_modtime
    BEFORE UPDATE ON schedule_bindings 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- 2. user_code_groups 表
DROP TRIGGER IF EXISTS trg_update_user_code_groups_modtime ON user_code_groups;
CREATE TRIGGER trg_update_user_code_groups_modtime
    BEFORE UPDATE ON user_code_groups 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- 3. user_contacts 表
DROP TRIGGER IF EXISTS update_user_contacts_modtime ON user_contacts;
CREATE TRIGGER update_user_contacts_modtime
    BEFORE UPDATE ON user_contacts 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();