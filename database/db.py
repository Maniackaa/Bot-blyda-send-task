import datetime
import uuid

from time import time
from typing import Sequence, List

from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer, MetaData, BigInteger, ARRAY, Table, Column, select, JSON
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker

from config_data.conf import conf, tz, get_my_loggers, BASE_DIR

logger, err_log = get_my_loggers()
metadata = MetaData()
# db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
# engine = create_engine(db_url, echo=False, max_overflow=-1)
engine = create_engine(conf.db.db_url, echo=False)

# db_path = BASE_DIR / 'db.sqlite3'
# engine = create_engine(f"sqlite:///{db_path}", echo=False)

Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    tg_id = mapped_column(String(30), unique=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=True)
    register_date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    referral: Mapped[str] = mapped_column(String(20), nullable=True)
    reports: Mapped[List['Report']] = relationship(back_populates='user', lazy='selectin')

    def __repr__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"}'

    def set(self, key, value):
        _session = Session()
        try:
            with _session:
                order = _session.query(User).filter(User.id == self.id).one_or_none()
                setattr(order, key, value)
                _session.commit()
                logger.debug(f'Изменено значение {key} на {value}')
        except Exception as err:
            err_log.error(f'Ошибка изменения {key} на {value}')
            raise err


class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    title: Mapped[str] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(String(4000), default='-')
    image: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20), default='photo')

    def __repr__(self):
        return f'{self.id}: {self.text[:20]}'

    @classmethod
    def get_items(cls):
        session = Session()
        with session:
            items_q = select(cls)
            items = session.execute(items_q).scalars().all()
            return items

    @classmethod
    def get_item(cls, num):
        session = Session()
        with session:
            item = select(cls).where(cls.id == num)
            item = session.execute(item).scalar()
            return item

    def get_nav_btn(self, num):
        nav_btn = {
            '<<': 'back',
            f'{num + 1}/{len(self.get_items())}': '-',
            '>>': 'fwd',
        }
        return nav_btn

    @classmethod
    def get_title_menu(cls):
        menus = []
        for item in cls.get_items():
            if item.title:
                menus.append([item.title, item.id])
        return menus


class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    user_id = mapped_column(ForeignKey('users.id'))
    user: Mapped[User] = relationship(back_populates="reports", lazy='selectin')
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    task_type:  Mapped[str] = mapped_column(String(20), default='утро')

    def __repr__(self):
        return f'Report {self.id}. {self.user} {self.date}'

Base.metadata.create_all(engine)