import requests
from sqlalchemy import create_engine, Column, Integer, String, Enum as SqlEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum

# --- Define Base and DB Setup ---
Base = declarative_base()
DATABASE_URL = "sqlite:///./chubby.db"  # adjust for your actual DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# --- Enum for hotelClass ---
class HotelClassEnum(str, Enum):
    chubby = "chubby"  # Placeholder for now

# --- Define HotelDB ---
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

# --- Create table ---
Base.metadata.create_all(bind=engine)

# --- Fetch hotels from SerpAPI ---
def fetch_hotels():
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_hotels",
        "q": "chicago",
        "check_in_date": "2025-08-16",
        "check_out_date": "2025-08-17",
        "hotel_class": "5",
        "api_key": API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def save_hotels_to_db(data):
    properties = data.get("properties", [])
    session = SessionLocal()

    for prop in properties:
        rate_info = prop.get("total_rate", {})
        rate = rate_info.get("extracted_lowest")

        # Skip if rate is missing
        if rate is None:
            continue

        # Determine hotelClass
        if 500 <= rate < 2000:
            hotel_class = HotelClassEnum.chubby
        elif rate >= 2000:
            hotel_class = HotelClassEnum.fat
        else:
            continue  # skip hotels with too low a rate

        hotel = HotelDB(
            name=prop.get("name", "Unknown"),
            description=prop.get("description", "No description"),
            address=prop.get("link", "No address"),
            country="USA",
            city="Chicago",
            zip="00000",
            hotelClass=hotel_class
        )
        session.add(hotel)

    session.commit()
    session.close()

# --- Run ---
if __name__ == "__main__":
    data = fetch_hotels()
    save_hotels_to_db(data)