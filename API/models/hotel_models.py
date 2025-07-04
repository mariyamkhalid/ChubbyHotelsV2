from sqlalchemy import Column, Integer, String,Float, Enum as SqlEnum, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from .enums import HotelClassEnum

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
    property_token = Column(String, nullable=True, unique=True)
    rate = Column(Integer, nullable=False)
    overall_rating = Column(Float, nullable=True)
    location_rating = Column(Float, nullable=True)
    HotelType = Column(String, nullable=True)
    link = Column(String, nullable=True)

    images = relationship("HotelImageDB", back_populates="hotel", cascade="all, delete-orphan")
    reviews = relationship("ReviewDB", back_populates="hotel", cascade="all, delete-orphan")

class HotelImageDB(Base):
    __tablename__ = "hotel_images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    image_url = Column(String, nullable=False)
    hotel = relationship("HotelDB", back_populates="images")
