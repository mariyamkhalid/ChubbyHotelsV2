from fastapi import FastAPI, HTTPException, Query, Form, File, UploadFile
from typing import List, Optional
from sqlalchemy.orm import joinedload
from models import Base, engine, SessionLocal, HotelClassEnum, HotelDB, HotelImageDB, Hotel, HotelImage, ReviewDB, ReviewImageDB, ReviewImageTypeEnum, ReviewResponse, ReviewCreate, UserDB, UserResponse
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

@app.get("/reviews/user/{user_id}", response_model=List[ReviewResponse])
def get_reviews_by_user(user_id: int):
    """
    Get all reviews by a specific user
    """
    with SessionLocal() as session:
        # First check if user exists
        user = session.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reviews = session.query(ReviewDB).options(
            joinedload(ReviewDB.user),
            joinedload(ReviewDB.hotel),
            joinedload(ReviewDB.images)
        ).filter(ReviewDB.user_id == user_id).all()
        
        return reviews

@app.post("/reviews", response_model=ReviewResponse)
async def create_review(
    hotel_id: int = Form(...),
    user_id: int = Form(...),
    setting_review: Optional[str] = Form(None),
    room_review: Optional[str] = Form(None),
    service_review: Optional[str] = Form(None),
    food_review: Optional[str] = Form(None),
    overall_review: str = Form(...),
    image_types: Optional[List[ReviewImageTypeEnum]] = Form(None),
    images: Optional[List[UploadFile]] = File(None)
):
    """
    Create a new review with optional multiple image uploads and image types.
    """
    # check if number of images and image types match
    if len(images) != len(image_types):
        raise HTTPException(status_code=400, detail="Number of images and image types must match")
    
    with SessionLocal() as session:
        hotel = session.query(HotelDB).filter(HotelDB.id == hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="Hotel not found")

        user = session.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        db_review = ReviewDB(
            hotel_id=hotel_id,
            user_id=user_id,
            setting_review=setting_review,
            room_review=room_review,
            service_review=service_review,
            food_review=food_review,
            overall_review=overall_review
        )

        session.add(db_review)
        session.commit()
        session.refresh(db_review)

        
        if images:
            for i, image in enumerate(images):
                if image.filename:
                    image_data = await image.read()
                    image_path = f"uploads/reviews/{db_review.id}_{i}_{image.filename}"
                    with open(image_path, "wb") as f:
                        f.write(image_data)

                    image_type = ReviewImageTypeEnum.overall  # default
                    if image_types and i < len(image_types) and image_types[i] in ReviewImageTypeEnum:
                        image_type = image_types[i]

                    review_image = ReviewImageDB(
                        review_id=db_review.id,
                        image_url=image_path,
                        image_type=image_type
                    )
                    session.add(review_image)

            session.commit()
            

        # Reload with relationships before session closes
        db_review_with_relations = session.query(ReviewDB).options(
            joinedload(ReviewDB.user),
            joinedload(ReviewDB.hotel),
            joinedload(ReviewDB.images)
        ).filter(ReviewDB.id == db_review.id).first()

        return db_review_with_relations

# ---------- User Endpoints ----------

@app.post("/users", response_model=UserResponse)
def create_user(name: str):
    """
    Create a new user
    """
    with SessionLocal() as session:
        user = UserDB(name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

@app.get("/users", response_model=List[UserResponse])
def get_users(user_id: Optional[int] = None):
    """
    Get all users or a specific user by ID
    """
    with SessionLocal() as session:
        if user_id is not None:
            user = session.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return [user]
        users = session.query(UserDB).all()
        return users
