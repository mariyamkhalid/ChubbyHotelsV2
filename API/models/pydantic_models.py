from pydantic import BaseModel
from typing import List, Optional
from .enums import HotelClassEnum

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
    rate: int
    overall_rating: Optional[float]
    location_rating: Optional[float]
    HotelType: Optional[str]
    link: Optional[str]

    class Config:
        orm_mode = True 