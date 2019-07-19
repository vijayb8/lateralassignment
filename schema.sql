DROP TABLE IF EXISTS "users";
CREATE TABLE "users" (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile VARCHAR(20) NOT NULL UNIQUE
);

DROP TABLE IF EXISTS "categories";
CREATE TABLE "categories" (
    id UUID PRIMARY KEY,
    category VARCHAR(100) NOT NULL UNIQUE
);

DROP TABLE IF EXISTS "products";
CREATE TABLE "products" (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price FLOAT NOT NULL,
    type UUID NOT NULL REFERENCES "categories"(id)
);

DROP TABLE IF EXISTS "orders";
CREATE TABLE "orders"(
    id SERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES "products"(id),
    user_id UUID NOT NULL REFERENCES "users"(id),
    purchased_at TIMESTAMP NOT NULL
);