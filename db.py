from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Устанавливаем соединение с базой данных (замените 'sqlite:///bot.db' на ваше соединение)
engine = create_engine('sqlite:///bot.db')
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    subscription_active = Column(Boolean, default=False)
    subscription_from = Column(DateTime, default = None)
    subscription_to = Column(DateTime, default = None)
    invite_link_retries = Column(Integer, default = 3)
    email = Column(String, nullable = True)
    promo_id =  Column(Integer, nullable = True)

class Promocode(Base):
    __tablename__ = 'promocodes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    discount = Column(Integer, nullable = True)
    days = Column(Integer, nullable = True)
    activations_left = Column(Integer)
    type = Column(String)

class PaymentMethod(Base):
    __tablename__ = 'payment_methods'
    
    id = Column(Integer, primary_key=True)
    network = Column(String)
    wallet_address = Column(String)


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    timestamp = Column(DateTime)
    method_id = Column(Integer)
    tariff_id = Column(Integer)
    comfired = Column(Boolean)


class Tariffs(Base):
    __tablename__ = 'tariffs'
    id = Column(Integer, primary_key=True)
    amount = Column(Integer)
    months = Column(Integer)


Base.metadata.create_all(engine)