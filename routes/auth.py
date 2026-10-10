from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from schemas.user_schema import UserCreate, UserResponse
from models.user_model import User
from database import get_db
from settings import settings


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# ============================================================
# OAUTH2
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


# ============================================================
# PASSWORD HASHING
# ============================================================

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str,hashed_password: str) -> bool:

    return password_hash.verify(plain_password,hashed_password)


def get_password_hash(password: str) -> str:

    return password_hash.hash(password)


# ============================================================
# REGISTER USER
# ============================================================

@router.post("/register_user",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
def registration(request: UserCreate,db: Session = Depends(get_db)):

    # Check whether user already exists
    is_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if is_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Hash password before storing it
    hashed_password = get_password_hash(
        request.password
    )

    # Create user
    new_user = User(
        name=request.name,
        email=request.email,
        hashed_password=hashed_password,
        gender=request.gender,
        year_of_birth=request.year_of_birth,
        medical_condition=request.medical_condition,
        allergy=request.allergy,
        blood_group=request.blood_group,
        phone_number=request.phone_number
    )

    # Save user
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(request: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):

    # OAuth2PasswordRequestForm uses "username".
    # Here we use username to receive the user's email.
    user = (
        db.query(User)
        .filter(User.email == request.username)
        .first()
    )

    # User does not exist
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # Verify password against stored Argon2 hash
    if not verify_password(
        request.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # Token expiration
    expire = (
        datetime.now(timezone.utc)
        + timedelta(minutes=settings.EXPIRY)
    )

    # Create JWT
    token = jwt.encode(
        {
            # Standard JWT subject claim
            "sub": str(user.id),

            # Expiration time
            "exp": expire
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================================
# GET CURRENT AUTHENTICATED USER
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    # Common authentication error
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:

        # Decode JWT
        payload = jwt.decode(token,settings.SECRET_KEY,algorithms=[settings.ALGORITHM])

        # Get user ID from JWT
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    except jwt.InvalidTokenError:

        raise credentials_exception

    # Find user in database
    user = (db.query(User).filter(User.id == user_id).first())

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    return user


# ============================================================
# TEST AUTHENTICATION ROUTE
# ============================================================

@router.get("/authentication")
def authenticate_user(
    current_user: User = Depends(get_current_user)
):

    return {
        "message": "Authentication successful",
        "user_id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email
    }