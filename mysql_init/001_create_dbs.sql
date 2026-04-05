CREATE DATABASE IF NOT EXISTS api_gateway_db;
CREATE DATABASE IF NOT EXISTS book_db;
CREATE DATABASE IF NOT EXISTS cart_db;
CREATE DATABASE IF NOT EXISTS catalog_db;
CREATE DATABASE IF NOT EXISTS comment_rate_db;
CREATE DATABASE IF NOT EXISTS customer_db;
CREATE DATABASE IF NOT EXISTS manager_db;
CREATE DATABASE IF NOT EXISTS order_db;
CREATE DATABASE IF NOT EXISTS pay_db;
CREATE DATABASE IF NOT EXISTS ship_db;
CREATE DATABASE IF NOT EXISTS staff_db;

GRANT ALL PRIVILEGES ON api_gateway_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON book_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON cart_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON catalog_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON comment_rate_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON customer_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON manager_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON order_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON pay_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON ship_db.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON staff_db.* TO 'app_user'@'%';

FLUSH PRIVILEGES;
