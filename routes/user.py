from fastapi import APIRouter, status, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from routes.auth import get_password_hash
from routes.auth import get_current_user
from models.user_model import User
from schemas.user_schema import UserUpdate, UserResponse, UserPasswordUpdate

router = APIRouter(
    prefix="/user",
    tags=["user"]
)


@router.put("/update", status_code=status.HTTP_202_ACCEPTED)
def update_user(
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Make sure the logged-in user can update this account

    user= db.query(User).filter(User.id==current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Unauthorized User')
    

    # Update fields
    user.name = request.name
    user.medical_condition= request.medical_condition
    user.allergy= request.allergy
    user.blood_group=request.blood_group
    user.year_of_birth=request.year_of_birth
    user.phone_number=request.phone_number
    
    db.commit()
    db.refresh(user)

    return {
        "message": "User updated successfully",
        "user": user
        
    }


@router.get('/getUser',response_model= UserResponse, status_code=status.HTTP_200_OK)
def show( db: Session=Depends(get_db) ,current_user: User = Depends(get_current_user)):

    user= db.query(User).filter(User.id==current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Unauthorized User')
        
    return user

@router.put("/updatePassword", status_code=status.HTTP_202_ACCEPTED)
def update_user(
    request: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Make sure the logged-in user can update this account
    user= db.query(User).filter(User.id==current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Unauthorized User')
    
    user.hashed_password=get_password_hash(request.password)
    db.commit()
    db.refresh(user)

    return {
        "message": "User updated successfully",
        "user": user
        
    }
