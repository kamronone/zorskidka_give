from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    start = State()
    verify = State()
    insta_username = State()
    examination = State()
    examination_yes = State()
    examination_no = State()
    send_yes = State()
    send_no = State()
    finish = State()

