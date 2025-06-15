from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String, create_engine, Enum as SqlEnum
from sqlalchemy.orm import sessionmaker, declarative_base
import enum
from typing import Optional

# ---------- SQLite Setup ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///./chubby.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# ---------- SQLAlchemy Enum ----------
class HotelClassEnum(enum.Enum):
    chubby = 'chubby'
    fat = 'fat'
    obese = 'obese'

# ---------- SQLAlchemy Model ----------
class HotelDB(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, index=True, nullable=False)
    address = Column(String, nullable=False)
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    zip = Column(String, nullable=False)
    hotelClass = Column(SqlEnum(HotelClassEnum), nullable=False)
    property_token = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# ---------- Pydantic Models ----------
class Hotel(BaseModel):
    id: int
    name: str
    description: str
    address: str
    country: str
    city: str
    zip: str
    hotelClass: HotelClassEnum
    property_token: Optional[str]
    image_url: Optional[str]

    class Config:
        orm_mode = True

class CreateHotel(BaseModel):
    name: str
    description: str
    address: str
    country: str
    city: str
    zip: str
    hotelClass: HotelClassEnum
    property_token: Optional[str]
    image_url: Optional[str]

    class Config:
        orm_mode = True

# ---------- FastAPI App ----------
app = FastAPI()

# ---------- Routes ----------

@app.get("/hotels", response_model=List[Hotel])
def get_hotels(
    hotel_id: Optional[int] = None,
    location: Optional[str] = Query(None, description="City or country name")
):
    with SessionLocal() as session:
        if hotel_id is not None:
            hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            return [hotel]

        query = session.query(HotelDB)
        if location:
            hotels = query.filter(
                (HotelDB.city.ilike(f"%{location}%")) |
                (HotelDB.country.ilike(f"%{location}%"))
            ).all()
        else:
            hotels = query.all()

        return hotels

@app.post("/hotels", response_model=Hotel)
def create_hotel(hotel: CreateHotel):
    with SessionLocal() as session:
        db_hotel = HotelDB(**hotel.dict())
        session.add(db_hotel)
        session.commit()
        session.refresh(db_hotel)
        return db_hotel

@app.delete("/hotels", response_model=Hotel)
def delete_hotel(hotel_id: int):
    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")
        session.delete(hotel)
        session.commit()
        return hotel
