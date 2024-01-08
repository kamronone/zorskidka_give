import mysql.connector

db_config = {
    'host': "127.0.0.1",
    'user': 'root',
    'password': '123456',
}

# Подключение к серверу MySQL
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Создание базы данных
try:
    cursor.execute("CREATE DATABASE draw_bot")
    print("База данных успешно создана.")
except mysql.connector.Error as err:
    print(f"Ошибка при создании базы данных: {err}")

# Переключение на созданную базу данных
try:
    cursor.execute("USE draw_bot")
    print("Используется база данных.")
except mysql.connector.Error as err:
    print(f"Ошибка при выборе базы данных: {err}")

# Создание таблицы участников
try:
    cursor.execute("""
        CREATE TABLE participants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            insta_username VARCHAR(255) NOT NULL,
            tg_username VARCHAR(255) NOT NULL
        )
    """)
    print("Таблица 'participants' успешно создана.")
except mysql.connector.Error as err:
    print(f"Ошибка при создании таблицы: {err}")

cursor.close()
conn.close()