import asyncio
import datetime
import logging
import random
from typing import Optional

from aiogram.types import Chat
from sqlalchemy import select, insert, update, delete

from config_data.conf import LOGGING_CONFIG, conf, tz, get_my_loggers


from database.db import User, Session, Task

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


def task_db_save(title, text, image):
    with Session() as session:
        task = Task(title=title, text=text, image=image)
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


if __name__ == '__main__':
    # num = 500134
    # digits_count = 5
    # result = f'{num:0{f"{digits_count}"}}'
    # print(result)
    print(asyncio.run(get_tasks_to_send()))