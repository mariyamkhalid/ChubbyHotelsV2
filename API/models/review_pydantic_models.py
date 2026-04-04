from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .enums import ReviewImageTypeEnum


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class HotelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    address: str


class ReviewImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    image_type: ReviewImageTypeEnum


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    setting_review: Optional[str]
    room_review: Optional[str]
    service_review: Optional[str]
    food_review: Optional[str]
    overall_review: Optional[str]
    user: UserResponse
    hotel: HotelResponse
    images: List[ReviewImageResponse] = []

class ReviewCreate(BaseModel):
    hotel_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    setting_review: Optional[str] = None
    room_review: Optional[str] = None
    service_review: Optional[str] = None
    food_review: Optional[str] = None
    overall_review: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hotel_id": 1,
                "email": "guest@example.com",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "overall_review": "Great stay.",
            }
        }
    )