import requests
from models import Base, engine, SessionLocal, HotelClassEnum, HotelDB, HotelImageDB, UserDB, ReviewDB
from sqlalchemy.exc import IntegrityError

# --- Create tables ---
Base.metadata.create_all(bind=engine)


def fetch_hotels_paginated(search_term: str, max_hotels=3000):
    url = "https://serpapi.com/search"
    all_properties = []
    next_page_token = None
    api_key = ""

    while len(all_properties) < max_hotels:
        print ("loading properties")
        params = {
            "engine": "google_hotels",
            "q": search_term,
            "check_in_date": "2025-10-16",
            "check_out_date": "2025-10-17",
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

        next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not next_page_token or not new_props:
            break

    return all_properties[:max_hotels]

# --- Save hotels and all images to DB ---

def save_hotels_to_db(properties):
    for prop in properties:
        print("Saving property")
        session = SessionLocal()

        try:
            rate_info = prop.get("total_rate", {})
            rate = rate_info.get("extracted_lowest")
            if rate is None:
                print("Skipping hotel- no rate")
                print(rate_info)
                continue

            if 500 <= rate < 2000:
                hotel_class = HotelClassEnum.chubby
            elif rate >= 2000:
                hotel_class = HotelClassEnum.fat
            else:
                print("Skipping hotel- rate is too low")
                continue

            token = prop.get("property_token")
            if not token:
                print("Skipping hotel- no token")
                continue

            coords = prop.get("gps_coordinates", {})
            geo_info = reverse_geocode(coords.get("latitude"), coords.get("longitude")) if coords else {}

            existing = session.query(HotelDB).filter_by(property_token=token).first()

            if existing:
                print("Updating existing hotel")
                # Update fields
                existing.name = prop.get("name", existing.name)
                existing.description = prop.get("description", existing.description)
                existing.address = prop.get("link", existing.address)
                existing.country = geo_info.get("country", existing.country)
                existing.city = geo_info.get("city", existing.city)
                existing.state = geo_info.get("state", existing.state)
                existing.province = geo_info.get("province", existing.province)
                existing.zip = geo_info.get("postcode", existing.zip)
                existing.continent = geo_info.get("continent", existing.continent)
                existing.hotelClass = hotel_class
                existing.rate = rate
                existing.overall_rating = prop.get("overall_rating", existing.overall_rating)
                existing.location_rating = prop.get("location_rating", existing.location_rating)
                existing.HotelType = prop.get("type", existing.HotelType)
                existing.link = prop.get("link", existing.link)

                # Clear and replace images
                existing.images.clear()
                for img in prop.get("images", []):
                    url = img.get("original_image")
                    if url:
                        existing.images.append(HotelImageDB(image_url=url))

            else:
                print("Adding new hotel")
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
                    property_token=token,
                    rate=rate,
                    overall_rating=prop.get("overall_rating"),
                    location_rating=prop.get("location_rating"),
                    HotelType=prop.get("type"),
                    link=prop.get("link")
                )

                for img in prop.get("images", []):
                    url = img.get("original_image")
                    if url:
                        hotel.images.append(HotelImageDB(image_url=url))

                session.add(hotel)

            session.commit()

        except IntegrityError as e:
            session.rollback()
            print(f"Skipped due to duplicate: {token} — {e.orig}")
        except Exception as e:
            session.rollback()
            print(f"Error processing hotel: {e}")
        finally:
            session.close()

def reverse_geocode(lat, lng):
    api_key = " 
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
    all_images = session.query(HotelImageDB).all()
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
