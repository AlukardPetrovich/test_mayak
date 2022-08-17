import os
import sqlite3
import time

import pandas
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

storage = MemoryStorage()
bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher(bot, storage=storage)
conn = sqlite3.connect('data.db')
cur = conn.cursor()
cur.execute(
    'CREATE TABLE IF NOT EXISTS added_by_user(name TEXT, url TEXT, xpath TEXT)'
    )
load_button = KeyboardButton('/Загрузить_файл')
cancel_button = KeyboardButton('/Отмена')
singl_button_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
singl_button_keyboard.add(load_button).add(cancel_button)


class FSMLoadFile(StatesGroup):
    file = State()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply('Начинаем работу', reply_markup=singl_button_keyboard)


async def data_processing(message, df):
    for _, row in df.iterrows():
        await message.answer(f'В обработку добавлены данные: {row}')
    df.to_sql('added_by_user', conn, if_exists='append', index=False)
    await message.answer('Все данные добавлены в обработку')


@dp.message_handler(commands='Загрузить_файл', state=None)
async def start_load(message: types.Message):
    await FSMLoadFile.file.set()
    await message.reply('Отправьте файл')


@dp.message_handler(content_types=['document'], state=FSMLoadFile.file)
async def get_file(message: types.Message, state: FSMContext):
    file_name = str(time.time()) + '.xls'
    if document := message.document:
        await document.download(
                destination_dir="",
                destination_file=file_name,
            )
    try:
        df = pandas.read_excel(
            file_name,
            header=None, names=['name', 'url', 'xpath']
        )
    except ValueError:
        await message.reply('данные принимаются только в .xls файлах')
        os.remove(file_name)
        return
    os.remove(file_name)
    await data_processing(message, df)
    await state.finish()


@dp.message_handler(state="*", commands='Отмена')
async def cancel_load(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Загрузка отменена')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
