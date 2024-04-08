from aiogram import Router, Bot, F
from aiogram.enums import ContentType
from aiogram.filters import Command, BaseFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ChatInviteLink, \
    InlineKeyboardButton, ChatMemberUpdated, FSInputFile, InputMediaPhoto, InputMediaDocument

from aiogram.fsm.context import FSMContext


from config_data.conf import get_my_loggers, BASE_DIR, conf
from database.db import Task
from keyboards.keyboards import yes_no_kb, start_kb, custom_kb, start_bn, nav_kb, confirm_kb
from lexicon.lexicon import LEXICON_RU

from services.db_func import get_or_create_user, task_db_save, task_db_delete

logger, err_log = get_my_loggers()


class IsAdmin(BaseFilter):
    def __init__(self) -> None:
        self.admins = conf.tg_bot.admin_ids

    async def __call__(self, message: Message) -> bool:
        result = str(message.from_user.id) in self.admins
        # print(f'Проверка на админа\n'
        #       f'{message}\n'
              # f'{message.from_user.id} in {self.admins}: {result}\n')
        return result


router: Router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class FSMTask(StatesGroup):
    send_photo = State()
    send_text = State()
    save_title = State()
    save_confirm = State()
    task_delete = State()


class FSMSendList(StatesGroup):
    list_edit = State()


@router.callback_query(F.data == 'cancel')
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await state.clear()
    await callback.message.answer('Бот приветствует вас!', reply_markup=start_kb)


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'/start {message.from_user.id}')
    await state.clear()
    referal = message.text[7:]
    new_user = get_or_create_user(message.from_user, referal)
    await message.answer('Бот приветствует вас!', reply_markup=start_kb)


# Добавление блюда-задачи
@router.callback_query(F.data == 'add_task')
async def echo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await callback.message.answer('Пришлите изображение')
    await state.set_state(FSMTask.send_photo)


@router.message(FSMTask.send_photo)
async def send_photo(message: Message, state: FSMContext, bot: Bot):
    # Прием фото

    if message.content_type == ContentType.PHOTO:
        file_id = message.photo[-1].file_id
        await state.update_data(image=file_id)
    else:
        await message.answer('Необходимо приложить изображение c сжатием')
        return

    await message.answer('Введите текст')
    await state.set_state(FSMTask.send_text)


@router.message(FSMTask.send_text)
async def answer_photo(message: Message, state: FSMContext, bot: Bot):
    # Прием текста
    text = message.text
    await state.update_data(text=text)
    await message.answer('Введите название')
    await state.set_state(FSMTask.save_title)


@router.message(FSMTask.save_title)
async def save_title(message: Message, state: FSMContext, bot: Bot):
    # Прием названия
    title = message.text
    await state.update_data(title=title)
    data = await state.get_data()
    image = data.get('image')
    text = data.get('text')
    await message.answer_photo(photo=image, caption=f'<b>{title}</b>\n{text}', reply_markup=confirm_kb)
    await state.set_state(FSMTask.save_confirm)


@router.callback_query(FSMTask.save_confirm, F.data.in_(['confirm']))
async def save_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if callback.data == 'confirm':
        data = await state.get_data()
        print(data)
        text = data.get('text')
        title = data.get('title')
        image = data.get('image')
        await callback.message.edit_reply_markup(reply_markup=None)
        task_id = task_db_save(title, text, image)
        await callback.message.answer(f'Сохранено #{task_id}', reply_markup=start_kb)
        await state.clear()


# Список блюд
def format_task_list() -> str:
    tasks = Task.get_items()
    if not tasks:
        return ''
    text = 'Список:\n'
    for task in tasks:
        text += f'<b>{task.id}. {task.title}</b>\n\n'
    return text


@router.callback_query(F.data == 'task_list')
async def echo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text(text=format_task_list(), reply_markup=start_kb)


@router.callback_query(F.data == 'task_del')
async def echo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_reply_markup(reply_markup=None)
    text = f'{format_task_list()}Введите номер для удаления'
    if not text:
        await callback.message.edit_text('Список пуст')
        return
    await callback.message.edit_text(text)
    await state.set_state(FSMTask.task_delete)


@router.message(FSMTask.task_delete)
async def task_delete(message: Message, state: FSMContext, bot: Bot):
    try:
        task_id = int(message.text.strip())
        await state.update_data(task_id=task_id)
        task = Task().get_item(task_id)
        if not task:
            await message.answer('Такого номера нет. Введите номер для удаления')
        else:
            await message.answer_photo(photo=task.image, caption=f'<b>{task.title}</b>\n{task.text}',
                                       reply_markup=custom_kb(2, {'Отмена': 'cancel', 'Удалить': f'delete_task_{task_id}'}))
            await state.set_state(FSMTask.task_delete)
    except ValueError:
        await message.answer('Введите корректный номер для удаления')


@router.callback_query(FSMTask.task_delete, F.data.startswith('delete_task_'))
async def task_delete_confirm(callback: CallbackQuery,  state: FSMContext, bot: Bot):
    await callback.message.delete()
    data = await state.get_data()
    task_id = data.get('task_id')
    result = task_db_delete(task_id)
    await state.clear()
    if result:
        await callback.message.answer('Удалено', reply_markup=start_kb)
    else:
        await callback.message.answer('Ошибка')


@router.callback_query(F.data.startswith('send_list_edit'))
async def send_list_edit(callback: CallbackQuery,  state: FSMContext, bot: Bot):
    await callback.message.delete()
    with open(BASE_DIR / 'send_list.txt') as file:
        send_list = file.read().strip()
    msg = await callback.message.answer(f'Текущий список:\n{send_list}\n\nВведите новый список через запятую', reply_markup=custom_kb(1, {'Отменить редактирование': 'cancel'}))
    await state.set_state(FSMSendList.list_edit)
    await state.update_data(msg=msg)


@router.message(FSMSendList.list_edit)
async def list_edit(message: Message, state: FSMContext, bot: Bot):
    try:
        new_send_list = message.text.strip()
        send_list_ids = [str(int(target_id.strip())) for target_id in new_send_list.split(',')]
        print(send_list_ids)
        with open(BASE_DIR / 'send_list.txt', 'w') as file:
            file.write(', '.join(send_list_ids))
        await message.answer(f'Новый список: {new_send_list}')
        data = await state.get_data()
        msg = data.get('msg')
        await bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as err:
        await message.answer(f'Ошибка: {err}', reply_markup=start_kb)
        await state.clear()



