from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import joinedload
from models import Base, engine, SessionLocal, HotelClassEnum, HotelDB, HotelImageDB, Hotel, HotelImage

# ---------- Create tables ----------
Base.metadata.create_all(bind=engine)


# ---------- FastAPI App ----------
app = FastAPI()

# ---------- Routes ----------

@app.get("/hotels", response_model=List[Hotel])
def get_hotels(
    hotel_id: Optional[int] = None,
    location: Optional[str] = Query(None, description="City or country name")
):
    with SessionLocal() as session:
        query = session.query(HotelDB).options(joinedload(HotelDB.images))

        if hotel_id is not None:
            hotel = query.filter(HotelDB.id == hotel_id).first()
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            return [hotel]

        if location:
            query = query.filter(
                (HotelDB.city.ilike(f"%{location}%")) |
                (HotelDB.country.ilike(f"%{location}%"))
            )

        hotels = query.all()
        return hotels

@app.delete("/hotels", response_model=Hotel)
def delete_hotel(hotel_id: int):
    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")
        session.delete(hotel)
        session.commit()
        return hotel
