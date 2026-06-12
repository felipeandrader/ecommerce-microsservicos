from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import pika
import json

DB_URL = "postgresql://admin:adminpassword@127.0.0.1:5435/orders_db"
SECRET_KEY = "chave_super_secreta_da_faculdade"
ALGORITHM = "HS256"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://127.0.0.1:5001/users/login")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    status = Column(String, default="Pendente")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Serviço de Pedidos")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("userId") is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

def publish_to_rabbitmq(message: dict):
    try:
        credentials = pika.PlainCredentials('user', 'password')
        connection = pika.BlockingConnection(pika.ConnectionParameters('127.0.0.1', 5672, '/', credentials))
        channel = connection.channel()
        
        channel.queue_declare(queue='order_created_queue', durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key='order_created_queue',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # Torna a mensagem persistente
        )
        connection.close()
    except Exception as e:
        print(f"Erro ao conectar no RabbitMQ: {e}")

class OrderCreate(BaseModel):
    product_id: int

class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    status: str


@app.post("/orders", response_model=OrderResponse)
def create_order(order: OrderCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.get("userId")
    
    new_order = Order(user_id=user_id, product_id=order.product_id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    evento = {
        "order_id": new_order.id,
        "user_id": user_id,
        "product_id": order.product_id,
        "status": new_order.status
    }
    publish_to_rabbitmq(evento)
    
    return new_order

@app.get("/orders/{user_id}", response_model=list[OrderResponse])
def get_user_orders(user_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") != "admin" and current_user.get("userId") != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão para ver pedidos de outro usuário")
        
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    return orders

@app.get("/health")
def health_check():
    return {"status": "ok"}