from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional
from .enums import HotelClassEnum


class HotelImage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_url: str
    # When set, serialized ``image_url`` becomes this S3 URL (not exposed as its own key).
    s3_url: Optional[str] = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _prefer_s3_image_url(self):
        s3 = (self.s3_url or "").strip()
        if not s3:
            return self
        if s3 == self.image_url:
            return self
        return self.model_copy(update={"image_url": s3})


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

    @model_validator(mode="after")
    def _only_include_s3_images(self):
        s3_images = [img for img in self.images if (img.s3_url or "").strip()]
        if len(s3_images) == len(self.images):
            return self
        return self.model_copy(update={"images": s3_images})

    model_config = ConfigDict(from_attributes=True)