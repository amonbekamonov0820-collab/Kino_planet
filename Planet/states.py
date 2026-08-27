from aiogram.fsm.state import State, StatesGroup


class MovieSearch(StatesGroup):
    waiting_code = State()


class AddMovie(StatesGroup):
    code = State()
    title = State()
    video = State()


class AddAdmin(StatesGroup):
    user_id = State()


class CreatePromo(StatesGroup):
    code = State()
    days = State()
    uses = State()


class CreateButton(StatesGroup):
    text = State()
    response = State()


class Broadcast(StatesGroup):
    content = State()


class EditMovieTitle(StatesGroup):
    value = State()


class EditMovieVideo(StatesGroup):
    value = State()


class RedeemPromo(StatesGroup):
    code = State()

class ForcedChannel(StatesGroup):
    add = State()