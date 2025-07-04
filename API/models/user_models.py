from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from .database import Base
from .enums import ReviewImageTypeEnum

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)

    reviews = relationship("ReviewDB", back_populates="user", cascade="all, delete-orphan")

class ReviewDB(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    setting_review = Column(String, nullable=True)
    room_review = Column(String, nullable=True)
    service_review = Column(String, nullable=True)
    food_review = Column(String, nullable=True)
    overall_review = Column(String, nullable=False)

    hotel = relationship("HotelDB", back_populates="reviews")
    user = relationship("UserDB", back_populates="reviews")
    images = relationship("ReviewImageDB", back_populates="review", cascade="all, delete-orphan") 

class ReviewImageDB(Base):
    __tablename__ = "review_images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    image_url = Column(String, nullable=False)
    image_type = Column(SqlEnum(ReviewImageTypeEnum), nullable=False)

    review = relationship("ReviewDB", back_populates="images")