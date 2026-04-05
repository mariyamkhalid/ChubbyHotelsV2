from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .enums import HotelClassEnum


class HotelImage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_url: str


class Hotel(BaseModel):
    id: int
    name: str
    description: str
    location: Optional[str] = None
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
    is_active: bool = True
    owner_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)