from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Form, File, UploadFile
from typing import List, Optional, Dict
from sqlalchemy.orm import Session, joinedload

from models import Base, engine, SessionLocal, HotelClassEnum, HotelDB, HotelImageDB, Hotel, ReviewDB, ReviewImageDB, ReviewImageTypeEnum, ReviewResponse, ReviewCreate, UserDB
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from fastapi.staticfiles import StaticFiles
# ---------- Create tables ----------
Base.metadata.create_all(bind=engine)


# ---------- FastAPI App ----------
app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # allow all domains
    allow_credentials=True,   # allow cookies and auth headers
    allow_methods=["*"],      # allow all HTTP methods
    allow_headers=["*"],      # allow all headers
)


def _get_or_create_user_by_email(
    session: Session,
    email: str,
    first_name: Optional[str],
    last_name: Optional[str],
) -> UserDB:
    email_clean = email.strip()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required")
    user = session.query(UserDB).filter(UserDB.email == email_clean).first()
    if user:
        return user
    fn = (first_name or "").strip() or None
    ln = (last_name or "").strip() or None
    user = UserDB(email=email_clean, first_name=fn, last_name=ln)
    session.add(user)
    session.flush()
    return user


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
                (HotelDB.country.ilike(f"%{location}%"))
            )

        hotels = query.all()
        return hotels


@app.post("/hotels", response_model=Hotel)
async def create_hotel(
    name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    email: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
):
    """
    Submit a new hotel (multipart). User is matched or created by email.
    Starts inactive (is_active=false) until approved; address mirrors location for legacy schema.
    Optional ``images``: repeat the field for multiple files (omit when none).
    """
    loc = location.strip()
    if not loc:
        raise HTTPException(status_code=400, detail="location is required")

    image_list = [f for f in (images or []) if getattr(f, "filename", None)]
    uploads_dir = Path("uploads/hotels")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        user = _get_or_create_user_by_email(session, email, first_name, last_name)
        hotel_row = HotelDB(
            name=name.strip(),
            description=description.strip(),
            location=loc,
            address=loc,
            hotelClass=HotelClassEnum.chubby,
            rate=0,
            is_active=False,
            owner_id=user.id,
        )
        session.add(hotel_row)
        session.commit()
        session.refresh(hotel_row)

        for i, image in enumerate(image_list):
            raw = await image.read()
            rel_path = f"uploads/hotels/{hotel_row.id}_{i}_{image.filename}"
            Path(rel_path).write_bytes(raw)
            session.add(HotelImageDB(hotel_id=hotel_row.id, image_url=rel_path))
        if image_list:
            session.commit()

        out = (
            session.query(HotelDB)
            .options(joinedload(HotelDB.images))
            .filter(HotelDB.id == hotel_row.id)
            .first()
        )
        if not out:
            raise HTTPException(status_code=500, detail="Hotel not found after create")
        return out


@app.get("/reviews", response_model=List[ReviewResponse])
def get_reviews(
    review_id: Optional[int] = None,
    hotel_id: Optional[int] = None,
    user_id: Optional[int] = None
):
    """
    Retrieve reviews with optional filtering by review_id, hotel_id, or user_id
    """
    with SessionLocal() as session:
        query = session.query(ReviewDB).options(
            joinedload(ReviewDB.user),
            joinedload(ReviewDB.hotel),
            joinedload(ReviewDB.images)
        )

        if review_id is not None:
            review = query.filter(ReviewDB.id == review_id).first()
            if not review:
                raise HTTPException(status_code=404, detail="Review not found")
            return [review]

        if hotel_id is not None:
            query = query.filter(ReviewDB.hotel_id == hotel_id)

        if user_id is not None:
            query = query.filter(ReviewDB.user_id == user_id)

        reviews = query.all()
        return reviews

@app.get("/reviews/hotel/{hotel_id}", response_model=List[ReviewResponse])
def get_reviews_by_hotel(hotel_id: int):
    """
    Get all reviews for a specific hotel
    """
    with SessionLocal() as session:
        # First check if hotel exists
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")

        reviews = session.query(ReviewDB).options(
            joinedload(ReviewDB.user),
            joinedload(ReviewDB.hotel),
            joinedload(ReviewDB.images)
        ).filter(ReviewDB.hotel_id == hotel_id).all()

        return reviews

@app.post("/reviews", response_model=ReviewResponse)
async def create_review(
    hotel_id: int = Form(...),
    email: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    setting_review: Optional[str] = Form(None),
    room_review: Optional[str] = Form(None),
    service_review: Optional[str] = Form(None),
    food_review: Optional[str] = Form(None),
    overall_review: str = Form(...),
    image_types: Optional[List[ReviewImageTypeEnum]] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
):
    """
    Multipart only. For ``application/json`` without files, use ``POST /reviews/json``.
    Omit ``images`` and ``image_types`` when there are no files.
    """
    image_list = images or []
    type_list = image_types or []
    if len(image_list) != len(type_list):
        raise HTTPException(status_code=400, detail="Number of images and image types must match")

    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")

        user = _get_or_create_user_by_email(session, email, first_name, last_name)

        db_review = ReviewDB(
            hotel_id=hotel_id,
            user_id=user.id,
            setting_review=setting_review,
            room_review=room_review,
            service_review=service_review,
            food_review=food_review,
            overall_review=overall_review
        )

        session.add(db_review)
        session.commit()
        session.refresh(db_review)


        if image_list:
            for i, image in enumerate(image_list):
                if image.filename:
                    image_data = await image.read()
                    image_path = f"uploads/reviews/{db_review.id}_{i}_{image.filename}"
                    with open(image_path, "wb") as f:
                        f.write(image_data)

                    image_type = ReviewImageTypeEnum.overall
                    if i < len(type_list) and type_list[i] in ReviewImageTypeEnum:
                        image_type = type_list[i]

                    review_image = ReviewImageDB(
                        review_id=db_review.id,
                        image_url=image_path,
                        image_type=image_type
                    )
                    session.add(review_image)

            session.commit()


        db_review_with_relations = session.query(ReviewDB).options(
            joinedload(ReviewDB.user),
            joinedload(ReviewDB.hotel),
            joinedload(ReviewDB.images)
        ).filter(ReviewDB.id == db_review.id).first()

        return db_review_with_relations


@app.post("/reviews/json", response_model=ReviewResponse)
def create_review_json(body: ReviewCreate):
    """
    JSON body (no images). In Swagger, JSON requests use **one** editor for the
    whole object—not separate boxes per field like multipart ``/reviews``.
    Open **Schema** below the editor to see each property and types.
    """
    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == body.hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")

        user = _get_or_create_user_by_email(
            session, body.email, body.first_name, body.last_name
        )

        db_review = ReviewDB(
            hotel_id=body.hotel_id,
            user_id=user.id,
            setting_review=body.setting_review,
            room_review=body.room_review,
            service_review=body.service_review,
            food_review=body.food_review,
            overall_review=body.overall_review,
        )
        session.add(db_review)
        session.commit()
        session.refresh(db_review)

        return (
            session.query(ReviewDB)
            .options(
                joinedload(ReviewDB.user),
                joinedload(ReviewDB.hotel),
                joinedload(ReviewDB.images),
            )
            .filter(ReviewDB.id == db_review.id)
            .first()
        )

# ---------- User Endpoints ----------

@app.get("/locations", response_model=Dict[str, List[str]])
def get_locations():
    """
    Distinct locations from hotels: continent name → sorted list of countries.

    Example: ``{"Europe": ["France", "Germany"], "Asia": ["Japan"]}``.
    """
    with SessionLocal() as session:
        rows = (
            session.query(HotelDB.continent, HotelDB.country)
            .filter(HotelDB.country.isnot(None))
            .filter(HotelDB.country != "")
            .distinct()
            .all()
        )

    by_continent: defaultdict[str, set[str]] = defaultdict(set)
    for continent, country in rows:
        c = country.strip()
        if not c:
            continue
        key = continent.strip() if continent and continent.strip() else "Other"
        by_continent[key].add(c)

    return {
        cont: sorted(by_continent[cont], key=str.casefold)
        for cont in sorted(by_continent.keys(), key=str.casefold)
    }