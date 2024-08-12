import asyncio

from aiogram import Router, Bot, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.media_group import MediaGroupBuilder

from config_data.conf import get_my_loggers, conf
from keyboards.keyboards import custom_kb, report_kb
from services.db_func import get_or_create_user, save_report, save_evening_report
from services.func import read_send_list_ids

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMSendGroup(StatesGroup):
    send_group = State()


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'/start {message.from_user.id}')
    user = get_or_create_user(message.from_user)
    await state.clear()
    await message.answer('Бот приветствует вас!')


@router.callback_query(F.data == 'start_report')
async def start_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начало ответа на задание"""
    await callback.answer('Вход в режим ответа')
    # caption = f'Отчет от {callback.from_user.id} {callback.from_user.username}\n'
    # caption += callback.message.caption
    media_group = MediaGroupBuilder()
    msg = callback.message
    await state.update_data(media_group=media_group, msg=msg)
    await callback.message.answer('Отправьте сжатое фото или видео для отчета (или несколько)')
    await state.set_state(FSMSendGroup.send_group)


@router.message(FSMSendGroup.send_group)
async def media_receiver(message: Message, state: FSMContext, bot: Bot):
    """Прием отправленных медиа для задания"""
    try:
        data = await state.get_data()
        media_group: MediaGroupBuilder = data.get('media_group')
        if message.photo:
            media_group.add_photo(media=message.photo[-1].file_id)
        await state.update_data(media_group=media_group)
        data = await state.get_data()
        if message.video:
            media_group.add_video(media=message.video.file_id)
        if message.document:
            media_group.add_document(media=message.document.file_id)
        msg: Message = data.get('msg')
        text = f'{msg.text or ""}' + f'\n\nДобавлено {len(media_group.build())} медиафайлов'
        await bot.edit_message_text(text=text, chat_id=message.chat.id, message_id=msg.message_id, reply_markup=report_kb)
        await asyncio.sleep(0.2)
        await message.answer('Медиафайлы добавлены. Отправьте еще медиа или Нажмите "Отправить отчет" на задании')

    except Exception as err:
        logger.error(err, exc_info=True)
        await message.answer(f'Ошибка: {err}')
        await state.clear()


@router.callback_query(F.data == 'report_reset')
async def report_reset(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg: Message = data.get('msg')
    await callback.message.edit_caption(caption=msg.caption, reply_markup=report_kb)
    await state.clear()


@router.callback_query(F.data == 'report_confirm')
async def echo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отправка отчета"""
    try:
        data = await state.get_data()
        media_group = data.get('media_group')
        if not media_group or not media_group.build():
            await callback.message.answer('Нет медиа для отправки')
            return
        # await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.edit_text(text=callback.message.text + '\nОтчет отправлен', reply_markup=report_kb)
        msg: Message = data.get('msg')
        media = media_group.build()
        tg_id = str(callback.from_user.id)
        name = read_send_list_ids()[tg_id]
        media[0].caption = f'Отчет от @{callback.from_user.username} ({name})\n' + msg.text
        await bot.send_media_group(chat_id=conf.tg_bot.admin_ids[0], media=media)
        await state.clear()
        user = get_or_create_user(callback.from_user)
        if 'олодильник' in msg.text:
            save_evening_report(user)
        else:
            save_report(user)
    except Exception as err:
        logger.error(err)


@router.callback_query()
async def echo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    print('echo')
    print(callback.data)