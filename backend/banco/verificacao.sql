SELECT VERSION(), @@hostname, @@port, @@bind_address;
SHOW VARIABLES WHERE Variable_name IN ('mysqlx_bind_address','general_log','log_bin');
SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='sistema';
SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES
WHERE TABLE_SCHEMA='sistema' AND TABLE_NAME IN ('usuarios','sessoes');
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='sistema' AND TABLE_NAME IN ('usuarios','sessoes')
ORDER BY ORDINAL_POSITION;
SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='sistema' AND TABLE_NAME IN ('usuarios','sessoes');
SELECT User, Host FROM mysql.user WHERE User='sistema_app';
-- Executar somente se a conta existir:
-- SHOW GRANTS FOR 'sistema_app'@'localhost';
