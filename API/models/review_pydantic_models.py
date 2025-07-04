from pydantic import BaseModel
from typing import List, Optional
from .enums import ReviewImageTypeEnum

class UserResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

class HotelResponse(BaseModel):
    id: int
    name: str
    description: str
    address: str

    class Config:
        orm_mode = True

class ReviewImageResponse(BaseModel):
    id: int
    image_url: str
    image_type: ReviewImageTypeEnum

    class Config:
        orm_mode = True

class ReviewResponse(BaseModel):
    id: int
    setting_review: Optional[str]
    room_review: Optional[str]
    service_review: Optional[str]
    food_review: Optional[str]
    overall_review: Optional[str]
    user: UserResponse
    hotel: HotelResponse
    images: List[ReviewImageResponse] = []

    class Config:
        orm_mode = True

class ReviewCreate(BaseModel):
    hotel_id: int
    user_id: int
    setting_review: Optional[str] = None
    room_review: Optional[str] = None
    service_review: Optional[str] = None
    food_review: Optional[str] = None
    overall_review: Optional[str] = None 