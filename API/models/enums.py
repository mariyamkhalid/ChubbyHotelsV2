from enum import Enum

class HotelClassEnum(str, Enum):
    chubby = "chubby"
    fat = "fat"
    obese = "obese" 

class ReviewImageTypeEnum(str, Enum):
    setting = "setting"
    room = "room"
    service = "service"
    food = "food"
    overall = "overall"