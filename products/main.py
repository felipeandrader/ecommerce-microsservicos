from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import itertools

DB_URL_1 = "postgresql://admin:adminpassword@127.0.0.1:5433/products_db_1"
DB_URL_2 = "postgresql://admin:adminpassword@127.0.0.1:5434/products_db_2"

engine1 = create_engine(DB_URL_1)
engine2 = create_engine(DB_URL_2)

SessionLocal1 = sessionmaker(autocommit=False, autoflush=False, bind=engine1)
SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String)
    preco = Column(Float, nullable=False)

Base.metadata.create_all(bind=engine1)
Base.metadata.create_all(bind=engine2)

app = FastAPI(title="Serviço de Produtos")

db_cycle = itertools.cycle([SessionLocal1, SessionLocal2])

def get_read_db():
    db_class = next(db_cycle)
    db = db_class()
    try:
        yield db
    finally:
        db.close()

SECRET_KEY = "chave_super_secreta_da_faculdade"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://127.0.0.1:5001/users/login")

def get_current_admin(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Credenciais inválidas")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role: str = payload.get("role")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acesso negado: requer privilégios de admin")
        return payload
    except JWTError:
        raise credentials_exception

class ProductCreate(BaseModel):
    nome: str
    descricao: str
    preco: float

class ProductResponse(BaseModel):
    id: int
    nome: str
    descricao: str
    preco: float


@app.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, admin: dict = Depends(get_current_admin)):
    db1 = SessionLocal1()
    db2 = SessionLocal2()
    
    try:
        # Salva na Réplica 1
        new_prod_1 = Product(**product.model_dump())
        db1.add(new_prod_1)
        db1.commit()
        db1.refresh(new_prod_1)

        new_prod_2 = Product(id=new_prod_1.id, **product.model_dump())
        db2.add(new_prod_2)
        db2.commit()

        return new_prod_1
    except Exception as e:
        db1.rollback()
        db2.rollback()
        raise HTTPException(status_code=500, detail="Erro de replicação: falha ao salvar nos bancos")
    finally:
        db1.close()
        db2.close()

@app.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_read_db)):
    return db.query(Product).all()

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_read_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return prod

@app.get("/health")
def health_check():
    return {"status": "ok"}