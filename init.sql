-- 1. Table : roles
CREATE TABLE IF NOT EXISTS role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- 2. Table : categories
CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 3. Table : users, avec clef étrangère vers role
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    role_id INTEGER REFERENCES role(id) ON DELETE SET NULL
);

-- 4. Table : products, avec clef étrangère vers category
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    category_id INTEGER REFERENCES category(id) ON DELETE SET NULL
);

-- 5. Table : orders, clef étrangère vers users
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL
);

-- 6. Table pivot : order_item, pour liaison N:N entre orders et products
CREATE TABLE IF NOT EXISTS order_item (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);

-- Index sur l’email (accélère la recherche et garantit unicité)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);


-- Index sur les FK users.role_id, products.category_id, orders.user_id, order_item.order_id, order_item.product_id
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_order_item_order_id ON order_item(order_id);
CREATE INDEX IF NOT EXISTS idx_order_item_product_id ON order_item(product_id);

-- Permissions pour l'utilisateur applicatif eya
CREATE USER eya WITH ENCRYPTED PASSWORD 'eyaalimi123';
GRANT CONNECT ON DATABASE usersdb TO eya;
GRANT USAGE ON SCHEMA public TO eya;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO eya;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO eya;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eya;


-- Facultatif : autorisations spécifiques pour séquences nouvellement créées
GRANT USAGE, SELECT ON SEQUENCE users_id_seq TO eya;
GRANT USAGE, SELECT ON SEQUENCE products_id_seq TO eya;
GRANT USAGE, SELECT ON SEQUENCE role_id_seq TO eya;
GRANT USAGE, SELECT ON SEQUENCE category_id_seq TO eya;
GRANT USAGE, SELECT ON SEQUENCE orders_id_seq TO eya;
GRANT USAGE, SELECT ON SEQUENCE order_item_id_seq TO eya;