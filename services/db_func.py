import asyncio
import datetime
import logging
import random
from typing import Optional

from aiogram.types import Chat
from sqlalchemy import select, insert, update, delete, func

from config_data.conf import LOGGING_CONFIG, conf, tz, get_my_loggers


from database.db import User, Session, Task, Report
from services.func import read_send_list_ids

logger, err_log = get_my_loggers()


def check_user(tg_id) -> User:
    """Возвращает найденного пользователя по tg_id"""
    logger.debug(f'Ищем юзера {tg_id}')
    session = Session(expire_on_commit=False)
    with session:
        q = select(User).where(User.tg_id == tg_id)
        user = session.execute(q).scalar()
        return user


def get_or_create_user(user, refferal=None) -> Optional[User]:
    """Из юзера ТГ создает User"""
    try:
        old_user = check_user(user.id)
        if old_user:
            logger.debug(f'Пользователь {old_user} есть в базе')
            return old_user
        # Создание нового пользователя
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=user.id,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            full_name=user.full_name,
                            username=user.username,
                            register_date=datetime.datetime.now(tz=tz),
                            referral=refferal
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


def task_db_save(title, text, image, content_type='image'):
    with Session() as session:
        task = Task(title=title, text=text, image=image, type=content_type)
        session.add(task)
        session.commit()
        return task.id


def task_db_delete(task_id):
    with Session() as session:
        q = delete(Task).where(Task.id == task_id)
        session.execute(q)
        session.commit()
        return True


async def get_tasks_to_send(n: int = 2):
    """Выбирает из всех задач случайные n"""
    with Session() as session:
        all_task_q = select(Task)
        all_task = session.execute(all_task_q).scalars().all()
        random.shuffle(all_task)
        return all_task[:n]


def save_report(user):
    with Session() as session:
        report = Report(user_id=user.id, date=datetime.datetime.now(tz=tz), task_type='утро')
        session.add(report)
        session.commit()


def save_evening_report(user, task_type=1):
    with Session() as session:
        report = Report(user_id=user.id, date=datetime.datetime.now(tz=tz), task_type='вечер')
        session.add(report)
        session.commit()


def get_expired_cafe() -> dict:
    """Возвращает словарь из send_list которые сегодня не прислали отчет"""
    session = Session(expire_on_commit=False)
    with session:
        q = select(Report)
        reports = session.execute(q).scalars().all()
        all_cafe = read_send_list_ids()
        logger.debug(f'Вcе кафе: {all_cafe}')
        for report in reports:
            print(report.date)
            if report.date.date() == datetime.datetime.now(tz=tz).date():
                all_cafe.pop(report.user.tg_id)
        logger.debug(f'Просроченные кафе: {all_cafe}')
        return all_cafe


def get_report(today=datetime.datetime.now(tz=tz).date()) -> str:
    """Текст недельного отчета"""
    try:
        send_list_ids = read_send_list_ids()
        cafe_report = '<b>Недельный отчет\n\n<b>'
        for tg_id, cafe_name in send_list_ids.items():
            cafe_report = f'Отчет по {cafe_name}.\n'
            user = check_user(tg_id)
            if user:
                cafe_report += f'Всего отчетов: {len(get_user_reports(user.id))}\n'
                expire_days = get_week_expire_report(user.id)
                cafe_report += f'Просрочено дней: {len(expire_days)}\n\n'
        logger.info(cafe_report)
        return cafe_report
    except Exception as err:
        logger.error(err)


def get_user_reports(user_id=1, task_type='утро') -> dict:
    """Все отчеты юзера за неделю"""
    try:
        session = Session(expire_on_commit=False)
        today = datetime.datetime.now(tz=tz).date()
        logger.info(f'Ищем репорты {user_id} за 7 дней от {today}')
        with session:
            q = select(Report).where(Report.task_type == task_type, Report.user_id == user_id,
                Report.date > today - datetime.timedelta(days=7))
            reports = session.execute(q).scalars().all()
            return reports
    except Exception as err:
        logger.error(err)


def get_week_expire_report(user_id=1, task_type='утро'):
    """Присылает просроченные отчеты юзера"""
    try:
        session = Session(expire_on_commit=False)
        today = datetime.datetime.now(tz=tz).date()
        logger.info(f'Ищем просрочку юзера {user_id} за 7 дней от {today}')
        with session:
            q = select(Report).where(Report.task_type == 'утро', Report.user_id == user_id,
                Report.date > today - datetime.timedelta(days=7)).where(
                func.extract('hour', Report.date) >= 10
            )
            exp_reports = session.execute(q).scalars().all()
            logger.debug(f'Просрочка юзера {user_id}: {exp_reports}')
            for report in exp_reports:
                print(report)
            return exp_reports
    except Exception as err:
        logger.error(err)


def evening_report_is_ok(user: User):
    """Если есть вечерний отчет до 23 то возвращает его"""
    today = datetime.datetime.now(tz=tz).date()
    session = Session(expire_on_commit=False)
    with session:
        q = select(Report).where(
            Report.user_id == user.id,
            Report.task_type == 'вечер',
            func.DATE(Report.date) == today,
            func.extract('hour', Report.date) < 23
        )
        res = session.execute(q).scalars().all()
        print(res)
    return res

if __name__ == '__main__':
    # num = 500134
    # digits_count = 5
    # result = f'{num:0{f"{digits_count}"}}'
    # print(result)
    # print(asyncio.run(get_tasks_to_send()))
    # get_expired_cafe()
    user_id = 2
    with Session() as session:
        q = delete(Report)
        session.execute(q)
        session.commit()
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 9, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 8, 11, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 7, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 5, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 4, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 3, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 2, 9, 5))
        session.add(report)
        report = Report(user_id=user_id, date=datetime.datetime(2024, 4, 1, 9, 5))
        session.add(report)
        session.commit()
        for x in range(1, 10):
            report = Report(user_id=user_id, date=datetime.datetime(2024, 4, x, 22, 5), task_type='вечер')
            session.add(report)
        session.commit()

    # get_week_expire_report()
    get_report()
    # get_evening_report(ch)
    user = check_user('6247356284')
    print(user)
    is_ok = evening_report_is_ok(user)
    print(is_ok)
