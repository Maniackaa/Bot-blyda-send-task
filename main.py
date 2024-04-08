import asyncio

import schedule
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError

from config_data.conf import conf, get_my_loggers, BASE_DIR
from handlers import user_handlers, admin_handlers
from keyboards.keyboards import report_kb
import aioschedule

from services.db_func import get_tasks_to_send

logger, err_log = get_my_loggers()


def read_send_list_ids():
    logger.debug('Чтение списка рассылки')
    try:
        with open(BASE_DIR / 'send_list.txt') as file:
            send_list = file.read().strip()
            send_list_ids = [str(int(target_id.strip())) for target_id in send_list.split(',') if target_id]
            logger.debug(f'Список прочитан:{send_list_ids}')
            return send_list_ids
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)


async def send_task(bot: Bot):
    try:
        logger.info('Начинаем рассылку')
        send_list_ids = read_send_list_ids()
        for send_id in send_list_ids:
            await asyncio.sleep(0.1)
            tasks = await get_tasks_to_send(8)
            logger.info(f'Задачи для {send_id}: {tasks}')
            for task in tasks:
                try:
                    await bot.send_photo(chat_id=send_id, photo=task.image, caption=f'{task.title}\n{task.text}', reply_markup=report_kb)
                    logger.info(f'Задача {task} пользователю {send_id} отправлена')
                    await asyncio.sleep(0.1)
                except TelegramForbiddenError as err:
                    logger.warning(f'Ошибка отправки сообщения для {send_id}: {err}')
                except Exception as err:
                    logger.error(f'ошибка отправки сообщения пользователю {send_id}: {err}', exc_info=False)
                    err_log.error(f'ошибка отправки сообщения пользователю {send_id}: {err}', exc_info=False)
    except Exception as err:
        logger.error(f'Ошибка дневное рассылки: {err}')
        err_log.error(err, exc_info=True)


async def shedulers(bot):
    "11:00 это 12:00 Мск"
    time_start1 = '7:00'
    aioschedule.every().day.at(time_start1).do(send_task, bot)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(5)


async def main():
    logger.info('Starting bot')
    bot: Bot = Bot(token=conf.tg_bot.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        admins = conf.tg_bot.admin_ids
        if admins:
            await bot.send_message(
                conf.tg_bot.admin_ids[0], f'Бот запущен.')
            logger.debug(f'Бот запущен.')
    except:
        err_log.critical(f'Не могу отравить сообщение {conf.tg_bot.admin_ids[0]}')
    # await send_task(bot)
    # all_jobs = schedule.get_jobs()
    # print(all_jobs)
    # await send_task(bot)
    await dp.start_polling(bot, allowed_updates=["message", "my_chat_member", "chat_member", "callback_query"])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')