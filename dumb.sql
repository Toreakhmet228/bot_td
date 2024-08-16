-- Таблица товаров
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,         
    price DECIMAL(10, 2) NOT NULL,      
    in_stock BOOLEAN DEFAULT TRUE,      
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE consumers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,       
    phone_number VARCHAR(20),            
    telegram_nickname VARCHAR(255)        
);
