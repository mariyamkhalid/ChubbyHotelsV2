from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import Column, Integer, String, create_engine, Enum as SqlEnum, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
import enum

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

# ---------- SQLAlchemy Models ----------
class HotelDB(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, index=True, nullable=False)
    address = Column(String, nullable=False)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    province = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    continent = Column(String, nullable=True)
    hotelClass = Column(SqlEnum(HotelClassEnum), nullable=False)
    property_token = Column(String, nullable=True)

    images = relationship("HotelImageDB", back_populates="hotel", cascade="all, delete-orphan")

class HotelImageDB(Base):
    __tablename__ = "hotel_images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    image_url = Column(String, nullable=False)

    hotel = relationship("HotelDB", back_populates="images")

Base.metadata.create_all(bind=engine)

# ---------- Pydantic Models ----------
class HotelImage(BaseModel):
    image_url: str

    class Config:
        orm_mode = True

class Hotel(BaseModel):
    id: int
    name: str
    description: str
    address: str
    country: Optional[str]
    city: Optional[str]
    zip: Optional[str]
    state: Optional[str]
    province: Optional[str]
    continent: Optional[str]
    hotelClass: HotelClassEnum
    property_token: Optional[str]
    images: List[HotelImage] = []

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
        query = session.query(HotelDB).options(joinedload(HotelDB.images))

        if hotel_id is not None:
            hotel = query.filter(HotelDB.id == hotel_id).first()
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            return [hotel]

        if location:
            query = query.filter(
                (HotelDB.city.ilike(f"%{location}%")) |
                (HotelDB.country.ilike(f"%{location}%"))
            )

        hotels = query.all()
        return hotels

@app.delete("/hotels", response_model=Hotel)
def delete_hotel(hotel_id: int):
    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")
        session.delete(hotel)
        session.commit()
        return hotel
