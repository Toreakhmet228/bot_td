import os
import logging
import psycopg2
from dotenv import load_dotenv
import nest_asyncio
import aiogram

# Загрузка переменных окружения
load_dotenv()
API_TELEGRAM=os.environ.get("TELEGRAM_BOT")

# Установка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к базе данных
def connect_db():
    conn = psycopg2.connect(
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        host="localhost",
        port="5432"
    )
    return conn

# Создание таблиц, если их нет
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        in_stock BOOLEAN NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consumers (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT NOT NULL UNIQUE,
        number TEXT,
        adress TEXT,
        
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL,
        consumer_id INTEGER NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (consumer_id) REFERENCES consumers (id)
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()

