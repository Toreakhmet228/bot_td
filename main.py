import os
import logging
import psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from dotenv import load_dotenv
import asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ.get("TELEGRAM_BOT"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")

class OrderForm(StatesGroup):
    address = State()
    number = State()
    username = State()
    product_id = State()
    photo = State()

class ProductForm(StatesGroup):
    name = State()
    price = State()
    in_stock = State()

def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get("POSTGRES_DB"),
            user=os.environ.get("POSTGRES_USER"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        logging.exception("Ошибка подключения к базе данных")
        raise e

def create_tables():
    conn = connect_db()
    cursor = None  # Инициализация переменной cursor
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS orders, consumers, products;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumers (
            id SERIAL PRIMARY KEY,
            telegram_id TEXT NOT NULL UNIQUE,
            number TEXT,
            address TEXT,
            username TEXT,
            product_name TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            in_stock BOOLEAN NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            consumer_id INTEGER NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (consumer_id) REFERENCES consumers (id)
        );
        """)

        conn.commit()
    except Exception as e:
        logging.exception("Ошибка при создании таблиц")
        raise e
    finally:
        if cursor:
            cursor.close()
        conn.close()

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поддержка"), KeyboardButton(text="Товары"), KeyboardButton(text="Заказать")],
        ],
        resize_keyboard=True
    )

    if message.from_user.id == int(ADMIN_TELEGRAM_ID):
        admin_buttons = [KeyboardButton(text="Добавить товар"), KeyboardButton(text="Все заказчики"), KeyboardButton(text="Удалить все товары"), KeyboardButton(text="Удалить всех заказчиков")]
        keyboard.keyboard.append(admin_buttons)

    await message.answer("Выберите команду:", reply_markup=keyboard)

@dp.message(F.text == "Добавить товар")
async def add_product_prompt(message: types.Message, state: FSMContext):
    if message.from_user.id == int(ADMIN_TELEGRAM_ID):
        await state.set_state(ProductForm.name)
        await message.answer("Введите название товара.")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

@dp.message(ProductForm.name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProductForm.price)
    await message.answer("Введите цену товара.")

@dp.message(ProductForm.price)
async def process_product_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(ProductForm.in_stock)
    await message.answer("Введите наличие товара (1 - в наличии, 0 - нет).")

@dp.message(ProductForm.in_stock)
async def process_product_in_stock(message: types.Message, state: FSMContext):
    conn = None
    cursor = None
    try:
        user_data = await state.get_data()
        name = user_data['name']
        price = float(user_data['price'])
        in_stock = bool(int(message.text))

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, price, in_stock) VALUES (%s, %s, %s)",
            (name, price, in_stock)
        )
        conn.commit()
        await message.answer("Товар успешно добавлен.")
    except Exception as e:
        logging.exception("Ошибка при добавлении товара")
        await message.answer(f"Ошибка при добавлении товара: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        await state.clear()

@dp.message(F.text == "Поддержка")
async def support(message: types.Message):
    await message.answer("Для поддержки свяжитесь с нами в Telegram: @elfshop_astana")

@dp.message(F.text == "Товары")
async def show_products(message: types.Message):
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, in_stock FROM products")
        products = cursor.fetchall()
        if not products:
            await message.answer("Товаров нет.")
        else:
            product_list = "\n".join([f"id-товара:{id}. {name} - {price}₸ {'(в наличии)' if in_stock else '(нет в наличии)'}" for id, name, price, in_stock in products])
            await message.answer(f"Список товаров:\n{product_list}")
    except Exception as e:
        logging.exception("Ошибка при получении списка товаров")
        await message.answer("Ошибка при получении списка товаров.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@dp.message(F.text == "Удалить все товары")
async def delete_all_products(message: types.Message):
    if message.from_user.id == int(ADMIN_TELEGRAM_ID):
        conn = None
        cursor = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products")
            conn.commit()
            await message.answer("Все товары были удалены.")
        except Exception as e:
            logging.exception("Ошибка при удалении всех товаров")
            await message.answer("Ошибка при удалении всех товаров.")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

@dp.message(F.text == "Удалить всех заказчиков")
async def delete_all_consumers(message: types.Message):
    if message.from_user.id == int(ADMIN_TELEGRAM_ID):
        conn = None
        cursor = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM consumers")
            conn.commit()
            await message.answer("Все данные о заказчиках были удалены.")
        except Exception as e:
            logging.exception("Ошибка при удалении всех заказчиков")
            await message.answer("Ошибка при удалении всех заказчиков.")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

@dp.message(F.text == "Все заказчики")
async def show_all_consumers(message: types.Message):
    if message.from_user.id == int(ADMIN_TELEGRAM_ID):
        conn = None
        cursor = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT username, number, address, product_name FROM consumers")
            consumers = cursor.fetchall()

            if not consumers:
                await message.answer("Нет зарегистрированных заказчиков.")
            else:
                consumer_list = "\n".join([f"Telegram: {username}, Номер: {number}, Адрес: {address}, Заказ: {product_name}" for username, number, address, product_name in consumers])
                await message.answer(f"Список заказчиков:\n{consumer_list}")
        except Exception as e:
            logging.exception("Ошибка при получении списка заказчиков")
            await message.answer("Ошибка при получении списка заказчиков.")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

@dp.message(F.text == "Заказать")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.address)
    await message.answer("Пожалуйста, отправьте свой адрес.")

@dp.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.number)
    await message.answer("Пожалуйста, отправьте свой номер телефона.")

@dp.message(OrderForm.number)
async def process_number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)
    await state.set_state(OrderForm.username)
    await message.answer("Пожалуйста, отправьте свой Telegram аккаунт.")

@dp.message(OrderForm.username)
async def process_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(OrderForm.product_id)
    await message.answer("Пожалуйста, введите ID товара, который хотите заказать.")

@dp.message(OrderForm.product_id)
async def process_product_id(message: types.Message, state: FSMContext):
    product_id = message.text
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        name, price = product
        await state.update_data(product_id=product_id, product_name=name, amount=price)
        await state.set_state(OrderForm.photo)
        await message.answer(f"""4400430212728452
Асылхан А.
Каспи банк. Перевод клиенту каспи. Перевести в течении 5 минут. Вы выбрали {name} за {price}₸. Теперь отправьте фото чека с суммой заказа.""")
    else:
        await message.answer("Товар с таким ID не найден. Попробуйте снова.")

@dp.message(F.photo, OrderForm.photo)
async def process_photo(message: types.Message, state: FSMContext):
    conn = None
    cursor = None
    try:
        user_data = await state.get_data()

        # Сохранение данных заказчика в базу
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consumers (telegram_id, number, address, username, product_name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
            number = EXCLUDED.number,
            address = EXCLUDED.address,
            username = EXCLUDED.username,
            product_name = EXCLUDED.product_name
        """, (str(message.from_user.id), user_data['number'], user_data['address'], user_data['username'], user_data['product_name']))
        conn.commit()

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{message.from_user.id}"),
                InlineKeyboardButton(text="Фейк", callback_data=f"reject_{message.from_user.id}")
            ]
        ])
        await bot.send_photo(
            ADMIN_TELEGRAM_ID,
            message.photo[-1].file_id,
            caption=f"Чек от пользователя {message.from_user.id}\nТовар: {user_data['product_name']}\nСумма: {user_data['amount']}₸\nНомер: {user_data['number']}\nАдрес: {user_data['address']}",
            reply_markup=markup
        )

        await message.answer("Ваш чек был отправлен администратору для проверки. Ожидайте подтверждения.")
    except Exception as e:
        logging.exception("Ошибка при обработке фотографии чека")
        await message.answer("Ошибка при обработке фотографии чека.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@dp.callback_query(F.data.startswith('confirm_'))
async def confirm_order(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.data.split('_')[1]

        # Убираем клавиатуру
        await callback_query.message.edit_reply_markup(reply_markup=None)

        await bot.send_message(user_id, "Ваш заказ подтвержден. Ожидайте доставку.")
        await callback_query.answer("Заказ подтвержден.")
    except Exception as e:
        logging.exception("Ошибка при подтверждении заказа")
        await callback_query.answer(f"Ошибка при подтверждении заказа: {e}")

@dp.callback_query(F.data.startswith('reject_'))
async def reject_order(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split('_')[1]
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Удаление данных заказчика
        cursor.execute("DELETE FROM consumers WHERE telegram_id = %s", (user_id,))
        conn.commit()

        # Убираем клавиатуру
        await callback_query.message.edit_reply_markup(reply_markup=None)
    
        await bot.send_message(user_id, "Ваш чек был отклонен. Пожалуйста, отправьте корректный чек.")
        await callback_query.answer("Чек отклонен. Сообщение отправлено заказчику.")
    except Exception as e:
        logging.exception("Ошибка при отклонении заказа")
        await callback_query.answer(f"Ошибка при отклонении заказа: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@dp.message(F.text)
async def unknown_command(message: types.Message):
    await message.answer("Пожалуйста, выберите одну из команд на клавиатуре ниже.")

async def main():
    create_tables()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
