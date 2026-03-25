from fastapi import FastAPI, HTTPException, status, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import timedelta
import time
from database import Database
from models import UserCreate, UserLogin, Token, UserResponse, HWIDBindRequest
from auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, verify_password
)
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Database.connect_to_mongo()
    yield
    # Shutdown
    Database.close_mongo_connection()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API Routes
@app.post("/api/register", response_model=Token)
async def register(user_data: UserCreate):
    db = Database.get_db()
    
    # Check if user exists
    existing_user = db.users.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Check if HWID is already bound to another account
    hwid_exists = db.users.find_one({"hwid": user_data.hwid})
    if hwid_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HWID already bound to another account"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user_dict = {
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "hwid": user_data.hwid,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(result.inserted_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=str(result.inserted_id),
            username=user_data.username,
            email=user_data.email,
            is_active=True,
            created_at=user_dict["created_at"],
            hwid_bound=True
        )
    }

@app.post("/api/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await authenticate_user(user_data.username, user_data.password, user_data.hwid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or HWID mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=str(user["_id"]),
            username=user["username"],
            email=user["email"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            hwid_bound=bool(user.get("hwid"))
        )
    }

@app.get("/api/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["_id"]),
        username=current_user["username"],
        email=current_user["email"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        hwid_bound=bool(current_user.get("hwid"))
    )

@app.post("/api/bind-hwid")
async def bind_hwid(
    hwid_data: HWIDBindRequest,
    current_user: dict = Depends(get_current_user)
):
    db = Database.get_db()
    
    # Check if HWID is already used
    existing = db.users.find_one({"hwid": hwid_data.hwid})
    if existing and existing["_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HWID already bound to another account"
        )
    
    # Bind HWID to current user
    db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"hwid": hwid_data.hwid}}
    )
    
    return {"message": "HWID bound successfully"}

# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.DEBUG)