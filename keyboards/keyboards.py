from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config_data.conf import conf

kb = [
    [KeyboardButton(text="/start")],
    ]

start_bn: ReplyKeyboardMarkup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


kb1 = {
    'Добавить блюдо': 'add_task',
    'Список': 'task_list',
    'Удалить': 'task_del',
    'Редактировать список рассылки': 'send_list_edit',
    'Отчет за 7 дней': 'send_report_7',
    'Отчет за 30 дней': 'send_report_30',
    # 'Прислать ответ': 'start_report'
}

report_btn = {
            'Добавить медиа для отчета': 'start_report',
            'Отправить отчет': 'report_confirm',
            'Сбросить': 'report_reset'
                 }


def custom_kb(width: int, buttons_dict: dict, back='', group='', menus='') -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons = []
    for key, val in buttons_dict.items():
        callback_button = InlineKeyboardButton(
            text=key,
            callback_data=val)
        buttons.append(callback_button)
    kb_builder.row(*buttons, width=width)
    if group:
        group_btn = InlineKeyboardButton(text='Обсудить в группе', url=group)
        kb_builder.row(group_btn)
    if menus:
        for menu in menus:
            item_btn = InlineKeyboardButton(text=menu[0], callback_data=f'menu_page_{menu[1]}')
            kb_builder.row(item_btn)
    if back:
        kb_builder.row(InlineKeyboardButton(text=back, callback_data='cancel'))
    return kb_builder.as_markup()


report_kb = custom_kb(1, report_btn)

start_kb = custom_kb(1, kb1)

yes_no_kb_btn = {
    'Да': 'yes',
    'Нет': 'no',
}
yes_no_kb = custom_kb(2, yes_no_kb_btn)

confirm_kb_btn = {
    'Отменить': 'cancel',
    'Подтвердить': 'confirm',
}
confirm_kb = custom_kb(2, confirm_kb_btn)
nav_btn = {
    '<<': 'back',
    '>>': 'fwd',
}

nav_kb = custom_kb(2, nav_btn)
