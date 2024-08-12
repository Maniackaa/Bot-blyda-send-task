import asyncio
import json
import random

import schedule
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from config_data.conf import conf, get_my_loggers, BASE_DIR
from handlers import user_handlers, admin_handlers
from keyboards.keyboards import report_kb
import aioschedule

from services.db_func import get_tasks_to_send, get_expired_cafe, check_user, evening_report_is_ok
from services.func import read_send_list_ids

logger, err_log = get_my_loggers()


async def send_task(bot: Bot):
    try:
        logger.info('Начинаем рассылку')
        await asyncio.sleep(random.randint(1, 30))
        send_list_ids = read_send_list_ids()
        for send_id, name in send_list_ids.items():
            try:
                await asyncio.sleep(0.1)
                tasks = await get_tasks_to_send(8)
                logger.info(f'Задачи для {name} {send_id}: {tasks}')
                task_title = f'{name}\n'
                for task in tasks:
                    if task.type == 'photo':
                        await bot.send_photo(chat_id=send_id, photo=task.image, caption=f'{task.title}\n{task.text}')
                    elif task.type == 'video':
                        await bot.send_video(chat_id=send_id, video=task.image, caption=f'{task.title}\n{task.text}')
                    task_title += f'{task.title}\n'
                    logger.info(f'Задача {task} пользователю {send_id} отправлена')
                    await asyncio.sleep(0.1)
                await bot.send_message(chat_id=send_id, text=task_title, reply_markup=report_kb)
            except TelegramForbiddenError as err:
                logger.warning(f'Ошибка отправки сообщения для {send_id}: {err}')
            except TelegramBadRequest as err:
                logger.warning(f'Ошибка отправки сообщения для {send_id}: {err}')
            except Exception as err:
                logger.error(f'ошибка отправки сообщения пользователю {send_id}: {err}', exc_info=False)
                err_log.error(f'ошибка отправки сообщения пользователю {send_id}: {err}', exc_info=False)


    except Exception as err:
        logger.error(f'Ошибка дневное рассылки: {err}')
        err_log.error(err, exc_info=True)


async def expired_cafe(bot: Bot):
    """Ищем ежденевные просрочки после 10.00 и шлём отчет"""
    try:
        logger.info(f'Ищем просрочки')
        expired_cafe_dict: dict = get_expired_cafe()
        text = ''
        for tg_id, name in expired_cafe_dict.items():
            text += f'Точка {name} нарушила сроки\n'
        if text:
            try:
                await bot.send_message(chat_id=conf.tg_bot.admin_ids[0], text=text)
                await bot.send_message(chat_id=conf.tg_bot.admin_ids[1], text=text)
                await asyncio.sleep(0.1)
            except TelegramForbiddenError as err:
                logger.warning(f'Ошибка отправки сообщения отчета по просрочки: {err}')
            except Exception as err:
                logger.error(f'Ошибка отправки сообщения отчета по просрочки: {err}', exc_info=False)

        else:
            logger.info('Просрочек нет')

    except Exception as err:
        logger.error(f'Ошибка проверки рассылки: {err}')


async def end_day_task(bot: Bot):
    """Задача по уборке холодильника вечером"""
    text = """Сфотографируй холодильники, микроволновку, рабочие поверхности и стеллажи, сухой склад, овощи."""
    try:
        logger.info('Начинаем вечернюю рассылку задачи')
        send_list_ids = read_send_list_ids()
        for send_id, name in send_list_ids.items():
            try:
                await asyncio.sleep(0.1)
                await bot.send_message(chat_id=send_id, text=text, reply_markup=report_kb)
            except TelegramForbiddenError as err:
                logger.warning(f'Ошибка отправки сообщения по уборке для {send_id}: {err}')
            except Exception as err:
                logger.error(f'ошибка отправки сообщения по уборке пользователю {send_id}: {err}', exc_info=False)
                err_log.error(f'ошибка отправки сообщения по уборке пользователю {send_id}: {err}', exc_info=False)
    except Exception as err:
        logger.error(err)


async def expired_evening_task(bot: Bot):
    """Ищем вечерние просрочки после 23.00 и шлём отчет"""
    try:
        logger.info(f'Ищем вечерние просрочки')
        povar_dict = read_send_list_ids()
        text = 'Вечерний отчет\n'
        for tg_id, name in povar_dict.items():
            user = check_user(tg_id)
            logger.debug(user)
            if user:
                is_ok = evening_report_is_ok(user)
                if not is_ok:
                    text += f'Точка @{name} нарушила сроки\n'
            else:
                text += f'Точки @{name} нет в базе\n'
        logger.debug(f'Отчет:\n{text}')
        await bot.send_message(chat_id=conf.tg_bot.admin_ids[0], text=text)
        await bot.send_message(chat_id=conf.tg_bot.admin_ids[1], text=text)
        logger.info(f'Отчет отправлен')
        await asyncio.sleep(0.1)

    except Exception as err:
        logger.error(f'Ошибка проверки рассылки: {err}')


async def shedulers(bot):
    """11:00 это 12:00 Мск"""
    time_start1 = '8:00'
    time_end = '11:00'
    aioschedule.every().day.at(time_start1).do(send_task, bot)
    aioschedule.every().day.at(time_end).do(expired_cafe, bot)
    # aioschedule.every(5).seconds.do(expired_cafe, bot)
    aioschedule.every().day.at('20:00').do(end_day_task, bot)
    end_day_task_time = '23:59'
    aioschedule.every().day.at(end_day_task_time).do(expired_evening_task, bot)

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
    # await end_day_task(bot)
    # await expired_evening_task(bot)
    asyncio.create_task(shedulers(bot))
    await dp.start_polling(bot, allowed_updates=["message", "my_chat_member", "chat_member", "callback_query"])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')