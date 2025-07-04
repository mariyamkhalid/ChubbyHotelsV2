import requests
from sqlalchemy import create_engine, Column, Integer, String, Enum as SqlEnum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from enum import Enum

# --- Define Base and DB Setup ---
Base = declarative_base()
DATABASE_URL = "sqlite:///./chubby.db"  # adjust for your actual DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# --- Enum for hotelClass ---
class HotelClassEnum(str, Enum):
    chubby = "chubby"  # Placeholder for now
    fat = "fat"

# --- Define HotelDB ---
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

    images = relationship("HotelImage", back_populates="hotel", cascade="all, delete-orphan")
    reviews = relationship("ReviewDB", back_populates="hotel", cascade="all, delete-orphan")

# --- Define HotelImage ---
class HotelImage(Base):
    __tablename__ = "hotel_images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    image_url = Column(String, nullable=False)

    hotel = relationship("HotelDB", back_populates="images")

# --- Define UserDB ---
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)

    reviews = relationship("ReviewDB", back_populates="user", cascade="all, delete-orphan")

# --- Define ReviewDB ---
class ReviewDB(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    review_text = Column(String, nullable=False)

    hotel = relationship("HotelDB", back_populates="reviews")
    user = relationship("UserDB", back_populates="reviews")

# --- Create tables ---
Base.metadata.create_all(bind=engine)

# --- Fetch hotels from SerpAPI ---
def fetch_hotels():
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_hotels",
        "q": "thailand",
        "check_in_date": "2025-08-16",
        "check_out_date": "2025-08-17",
        "hotel_class": "5",
        "api_key": "",  # <-- insert your API key here
        "rating": "9"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_hotels_paginated(search_term: str, max_hotels=1000):
    url = "https://serpapi.com/search"
    all_properties = []
    next_page_token = None
    api_key = ""

    while len(all_properties) < max_hotels:
        print ("loading properties")
        params = {
            "engine": "google_hotels",
            "q": search_term,
            "check_in_date": "2025-08-16",
            "check_out_date": "2025-08-17",
            "hotel_class": "5",
            "rating": "9",
            "api_key": api_key
        }

        if next_page_token:
            params["next_page_token"] = next_page_token

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        new_props = data.get("properties", [])
        all_properties.extend(new_props)

        # ✅ Corrected: Extract token from nested 'serpapi_pagination'
        next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not next_page_token or not new_props:
            break

    return all_properties[:max_hotels]

# --- Save hotels and all images to DB ---
def save_hotels_to_db(properties):
    session = SessionLocal()

    for prop in properties:
        print ("saving property")
        token = prop.get("property_token")
        if token:
            # Check for existing hotel with the same token
            existing = session.query(HotelDB).filter_by(property_token=token).first()
            if existing:
                continue  # Skip duplicates
        rate_info = prop.get("total_rate", {})
        rate = rate_info.get("extracted_lowest")

        if rate is None:
            continue

        if 500 <= rate < 2000:
            hotel_class = HotelClassEnum.chubby
        elif rate >= 2000:
            hotel_class = HotelClassEnum.fat
        else:
            continue

        coords = prop.get("gps_coordinates", {})
        geo_info = reverse_geocode(coords.get("latitude"), coords.get("longitude")) if coords else {}

        hotel = HotelDB(
            name=prop.get("name", "Unknown"),
            description=prop.get("description", "No description"),
            address=prop.get("link", "No address"),
            country=geo_info.get("country"),
            city=geo_info.get("city"),
            state=geo_info.get("state"),
            province=geo_info.get("province"),
            zip=geo_info.get("postcode"),
            continent=geo_info.get("continent"),
            hotelClass=hotel_class,
            property_token=prop.get("property_token"),
        )

        for img in prop.get("images", []):
            url = img.get("original_image")
            if url:
                hotel.images.append(HotelImage(image_url=url))

        session.add(hotel)

    session.commit()
    session.close()

def reverse_geocode(lat, lng):
    api_key = ""  # Replace with your real key
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data["results"]:
            return {k: None for k in ["city", "state", "province", "postcode", "country", "continent"]}

        components = data["results"][0]["components"]
        return {
            "city": components.get("city") or components.get("town") or components.get("village"),
            "state": components.get("state"),
            "province": components.get("province"),
            "postcode": components.get("postcode"),
            "country": components.get("country"),
            "continent": components.get("continent")
        }

    except Exception as e:
        print(f"Reverse geocoding failed for ({lat}, {lng}): {e}")
        return {k: None for k in ["city", "state", "province", "postcode", "country", "continent"]}

# --- Remove broken image URLs from DB ---
def clean_broken_images():
    session = SessionLocal()
    all_images = session.query(HotelImage).all()
    removed_count = 0
    image_count = 0
    for image in all_images:
        image_count =image_count + 1
        try:
            response = requests.head(image.image_url, timeout=5)
            if response.status_code >= 400:
                session.delete(image)
                removed_count += 1
        except Exception:
            session.delete(image)
            removed_count += 1
        print("done")
        print(removed_count)
        print(image_count)

    session.commit()
    session.close()
    print(f"Removed {removed_count} broken images.")

if __name__ == "__main__":
    choice = input("Enter 'fetch' to fetch and save hotels, or 'clean' to remove broken images: ").strip().lower()

    if choice == "fetch":
        search_term = input("Enter a location to search hotels for (e.g., 'thailand', 'chicago'): ").strip()
        if not search_term:
            print("Search term cannot be empty.")
        else:
            data = fetch_hotels_paginated(search_term)
            save_hotels_to_db(data)
            print(f"Hotel data saved for: {search_term}")
    elif choice == "clean":
        clean_broken_images()
    else:
        print("Invalid choice. Please enter 'fetch' or 'clean'.")
