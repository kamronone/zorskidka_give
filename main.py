import json
import logging
import asyncio
import sys
import datetime
from aiogram.client import bot
import mysql.connector
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from States.state import Form
from aiogram.types import Message
from aiogram import F
from keyboard.inline.inline_keyboard import social_keyboard, get_keyboard, send
import requests
import os
from dotenv import load_dotenv

load_dotenv()

db_params = {
    "host": os.getenv('HOSTNAME_DB'),
    "user": os.getenv('USER_DB'),
    "password": os.getenv('PASSWORD_DB'),
    "database": os.getenv('DATABASE_DB'),
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv('TOKEN'), parse_mode=ParseMode.HTML)
dp = Dispatcher()

router = Router()

conn = mysql.connector.connect(**db_params)
cursor = conn.cursor()


async def delete_message(chat_id, message_id):
    await bot.delete_message(chat_id=chat_id, message_id=message_id)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    tg_username = message.from_user.username
    if not tg_username:
        tg_username = "None"
    await state.update_data(user_id=user_id, tg_username=tg_username)
    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO participants (tg_user_id, tg_username) VALUES (%s, %s)",
                   (user_id, tg_username))
    conn.commit()

    await state.set_state(Form.verify)
    await message.answer("Для участия в еженедельном розыгрыше от ZorSkidka подпишитесь на наши каналы!",
                         reply_markup=social_keyboard.as_markup())


@router.message(Form.verify)
@dp.callback_query(F.data == "verify")
async def send_verify_value(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer()

    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM participants WHERE tg_user_id = %s", (user_id,))
    existing_user = cursor.fetchone()

    try:
        chat_member = await bot.get_chat_member(chat_id="-1001827915633", user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise ValueError("Вы не подписались на Telegram канал.")
    except Exception as e:
        await callback.message.answer(f"Вы не подписались на Telegram канал.")
        return

    if not existing_user:
        conn = mysql.connector.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO participants (tg_user_id, verified) VALUES (%s, 1)", (user_id,))
        conn.commit()

    await state.set_state(Form.examination)
    await callback.message.answer(
        "Пожалуйста, напишите свой никнейм в Instagram:")


@router.message(Form.examination)
@dp.message(Form.examination)
async def examination_test(message: types.Message, state: FSMContext):
    insta_username = message.text
    print(f"Instagram username received: {insta_username}")
    try:
        await message.answer(f"Вы правильно указали Instagram никнейм: {insta_username}?\n",
                             reply_markup=get_keyboard())
        await state.update_data(insta_username=insta_username)
        await state.set_state(Form.examination_yes)
    except Exception as e:
        print(e)
        await message.answer('Попробуйте заново ввести свой username пожалуйста.')
        await state.set_state(Form.examination)


@router.message(Form.examination_no)
@dp.callback_query(F.data == "no")
async def callbacks_num(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Вы нажали 'Нет'. Пожалуйста, введите правильный Instagram никнейм.")
    await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)

    await state.set_state(Form.examination)
    await state.update_data(insta_username=None)


@router.message(Form.examination_yes)
@dp.callback_query(F.data == "yes")
async def get_contact(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = await state.get_data()
    insta_username = data.get('insta_username')
    tg_username = data.get('tg_username')
    user_id = data.get('user_id')
    cookies = data.get('cookies')
    headers = data.get('headers')

    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    try:
        # Проверяем подписку пользователя
        is_subscribed = await check_insta_subscription(insta_username, cookies, headers, state)
        print(is_subscribed)
        if is_subscribed:
            cursor.execute("SELECT * FROM give WHERE id_tg = %s", (user_id,))
            existing_user = cursor.fetchone()

            if existing_user:
                await callback.message.answer('Вы уже зарегистрированы. Спасибо!')
                await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
                await state.clear()
            else:
                cursor.execute(
                    "INSERT INTO give (username_tg, id_tg, username_insta, add_date) VALUES (%s, %s, %s, %s)",
                    (tg_username, user_id, insta_username, current_datetime))
                conn.commit()
                await state.clear()
                await callback.message.answer('Принято вы стали участником акции от ZorSkidka. Спасибо!')
                await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
        else:
            await state.set_state(Form.examination)
            await callback.message.answer(
                'Вы не подписаны на наш Instagram. Пожалуйста, укажите свое Instagram-имя заново:')
            await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
            await callback.message.delete()

    except Exception as e:
        print(f"Произошла ошибка при выполнении запроса: {str(e)}")


async def check_telegram_subscription(user_id):
    try:
        chat_member = await bot.get_chat_member(chat_id="-1001827915633", user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        return False


async def check_insta_subscription(username_insta, cookies, headers, state: FSMContext):
    data = await state.get_data()
    insta_username = data.get('insta_username')[:20]
    print(insta_username)
    cookies = {
        'mid': 'ZTEXhgALAAHvuhsWFfl1BHIxwmjI',
        'ig_did': 'C3EA041D-4977-45BC-B7D3-8F7CDA4C24C7',
        'ig_nrcb': '1',
        'datr': 'hBcxZfJkv5tG7PBUwLcv6OoG',
        'csrftoken': 'N0xLTmLrUmXf0ZnmvvkCJGdWKooJivAD',
        'ds_user_id': '57250310092',
        'shbid': '"6806\\05457250310092\\0541735899285:01f70616a85684491e29e9393b3935ee845da06c3e3f7cec74643bc93f7a60a67b6004d1"',
        'shbts': '"1704363285\\05457250310092\\0541735899285:01f7f655a3211be6b9288d98da5c7ccd0d5d1f5dbd8c8f6985d8d34b17891d385dce40d3"',
        'sessionid': '57250310092%3AowqPHYgIwB4Lce%3A16%3AAYfjhMgryXiGQtQoHFg-qPE52qLL-Jq44m5vy68Tzg',
        'rur': '"LDC\\05457250310092\\0541736100097:01f7bf33738f62222441c80b983363aa118a9e3edfd529c35c0d6824b6e55e7f9f054e32"',
    }

    headers = {
        'authority': 'www.instagram.com',
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'dpr': '1',
        'pragma': 'no-cache',
        'referer': 'https://www.instagram.com/zorskidka/followers/',
        'sec-ch-prefers-color-scheme': 'light',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-full-version-list': '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.199", "Google Chrome";v="120.0.6099.199"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'viewport-width': '1920',
        'x-asbd-id': '129477',
        'x-csrftoken': 'N0xLTmLrUmXf0ZnmvvkCJGdWKooJivAD',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0e5mwdXZEAkgMH-y8xzASuXuWVo23qxquTlMeQDVDhgrUL',
        'x-requested-with': 'XMLHttpRequest',
    }
    params = {
        'count': '12',
        'query': str(insta_username),
        'search_surface': 'follow_list_page',
    }

    response = requests.get(
        'https://www.instagram.com/api/v1/friendships/60865511102/followers/',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    content = response.content
    decode = content.decode()
    users = json.loads(decode)
    usernames = [user["username"] for user in users["users"]]
    print(usernames)
    return username_insta in usernames


@router.message(Command("random", prefix="/"))
@dp.message(Command("random", prefix="/"))
async def random_winner(message: types.Message, state: FSMContext):
    allowed_user_id = 6129302314
    if message.from_user.id == allowed_user_id:

        conn = mysql.connector.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username_tg, username_insta, id_tg, blocked FROM give WHERE blocked IS NULL OR blocked < NOW() "
            "ORDER BY RAND() LIMIT 1")
        winner_data = cursor.fetchone()

        if winner_data:
            winner_username = winner_data[0]
            winner_username_insta = winner_data[1]
            winner_id = winner_data[2]
            await state.update_data(winner_id=winner_id)

            is_telegram_subscribed = await check_telegram_subscription(message.from_user.id)

            if is_telegram_subscribed:
                winner_link = f'<a href="https://t.me/{winner_username}">{winner_username}</a>'

                blocked_until = datetime.datetime.now() + datetime.timedelta(days=20)
                cursor.execute("UPDATE give SET blocked = %s WHERE username_tg = %s",
                               (blocked_until, winner_username))
                conn.commit()

                message_text = (f"Победитель: {winner_link}.\nInstagram username: <a href='https://www.instagram.com/{winner_username_insta}'>{winner_username_insta}</a>\n"
                                f"Заблокирован на 20 дней.\nХотите отправить всем "
                                f"сообщение кто победитель")
                await message.answer(message_text, parse_mode=ParseMode.HTML, reply_markup=send())
            else:
                not_subscribed_text = "Победитель не подписан на"

                if not is_telegram_subscribed:
                    not_subscribed_text += " телеграм"

                not_subscribed_text += f". Выберите другого участника.\n"

                if not is_telegram_subscribed:
                    not_subscribed_text += f"Telegram username: <a href='https://t.me/{winner_username}'>{winner_username}</a>\nInstagram username: {winner_username_insta}\n"

                await message.answer(not_subscribed_text, parse_mode='HTML')
        else:
            await message.answer("Нет доступных участников в розыгрыше.")
    else:
        await message.answer("Извините, у вас нет разрешения использовать эту команду.")


@router.message(Form.send_yes)
@dp.callback_query(F.data == "random_yes")
async def send_message_to_all(message: types.Message, state: FSMContext):
    allowed_user_id = 6129302314
    if message.from_user.id == allowed_user_id:
        conn = mysql.connector.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute("SELECT id_tg FROM give")
        participants = cursor.fetchall()
        conn.close()
        data = await state.get_data()
        winners = data.get('winner_id')
        print(winners)
        for participant in participants:
            user_id = participant[0]
            try:
                if user_id != winners:
                    regular_message = ("Уважаемые подписчики канала ZorSkidka мы определили победителя в нашем "
                                       "розыгрыше и скоро объявим про это в нашем Telegram "
                                       f"канале <a href='https://t.me/ZorSkidka'>ZorSkidka</a>.\nСледите за новостями "
                                       "скоро ещё будут розыгрыши")
                    await bot.send_message(user_id, regular_message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения участнику {user_id}: {str(e)}")

        try:
            winner_message = ("Поздравляем! 🥳 Вы стали победителем акции от <a "
                              "href='https://t.me/ZorSkidka'>ZorSkidka</a>, в ближайшее время с вами свяжется "
                              "администратор для вручения подарка.")
            await bot.send_message(winners, winner_message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения победителю {winners}: {str(e)}")

        await message.answer("Сообщения отправлены всем участникам.")


@router.message(Form.send_no)
@dp.callback_query(F.data == "random_no")
async def clear_state(message: types.Message, state: FSMContext):
    await message.answer("Хорошо не отправим никому")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
