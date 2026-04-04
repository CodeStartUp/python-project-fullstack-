from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from contextlib import asynccontextmanager
from typing import Optional
import os

from database import connect_to_mongo, close_mongo_connection, db, get_current_time
from models import UserCreate, UserLogin, ScoreUpdate
import auth
from config import settings

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up Flappy Bird & Parkour Game Server...")
    await connect_to_mongo()
    print("✅ Database connected successfully!")
    yield
    # Shutdown
    print("🛑 Shutting down server...")
    await close_mongo_connection()
    print("✅ Database connection closed!")

# Create FastAPI app
app = FastAPI(title="Flappy Bird & Parkour Game", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Helper function to get current user
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    username = auth.verify_token(token)
    if not username:
        return None
    user = await db.db.users.find_one({"username": username})
    return user

# ==================== WEB ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with login/register options"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard showing user stats and high scores for both games"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    username = auth.verify_token(token)
    if not username:
        return RedirectResponse(url="/", status_code=303)
    
    user = await db.db.users.find_one({"username": username})
    
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    # Get leaderboard for Flappy Bird
    flappy_leaderboard = await db.db.users.find(
        {}, 
        {"username": 1, "high_score": 1, "_id": 0}
    ).sort("high_score", -1).limit(10).to_list(None)
    
    # Get leaderboard for Parkour
    parkour_leaderboard = await db.db.users.find(
        {}, 
        {"username": 1, "parkour_score": 1, "_id": 0}
    ).sort("parkour_score", -1).limit(10).to_list(None)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": username,
        "high_score": user.get("high_score", 0),
        "parkour_score": user.get("parkour_score", 0),
        "total_games": user.get("total_games", 0),
        "flappy_leaderboard": flappy_leaderboard,
        "parkour_leaderboard": parkour_leaderboard
    })

@app.get("/game-select", response_class=HTMLResponse)
async def game_select(request: Request):
    """Game selection page"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    username = auth.verify_token(token)
    if not username:
        return RedirectResponse(url="/", status_code=303)
    
    user = await db.db.users.find_one({"username": username})
    
    return templates.TemplateResponse("game_select.html", {
        "request": request,
        "username": username,
        "high_score": user.get("high_score", 0),
        "parkour_score": user.get("parkour_score", 0)
    })

@app.get("/game", response_class=HTMLResponse)
async def flappy_game(request: Request):
    """Flappy Bird Game page"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    username = auth.verify_token(token)
    if not username:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("game.html", {
        "request": request,
        "username": username
    })

@app.get("/parkour-game", response_class=HTMLResponse)
async def parkour_game(request: Request):
    """3D Parkour Game page"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    username = auth.verify_token(token)
    if not username:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("parkour.html", {
        "request": request,
        "username": username
    })

# ==================== API ROUTES ====================

@app.post("/api/register")
async def register_user(user_data: UserCreate):
    """Register new user"""
    try:
        # Check if username or email exists
        existing_user = await db.db.users.find_one({
            "$or": [
                {"username": user_data.username},
                {"email": user_data.email}
            ]
        })
        
        if existing_user:
            if existing_user.get("username") == user_data.username:
                raise HTTPException(status_code=400, detail="Username already exists")
            else:
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create new user
        hashed_password = auth.get_password_hash(user_data.password)
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "high_score": 0,          # Flappy Bird high score
            "parkour_score": 0,        # Parkour game high score
            "total_games": 0,
            "best_level": 1,
            "avg_score": 0,
            "created_at": get_current_time()
        }
        
        result = await db.db.users.insert_one(user_dict)
        
        return JSONResponse(
            status_code=201,
            content={"message": "User created successfully", "username": user_data.username}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/login")
async def login_user(user_data: UserLogin):
    """Login user and return token"""
    try:
        # Find user
        user = await db.db.users.find_one({"username": user_data.username})
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify password
        if not auth.verify_password(user_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Create token
        token = auth.create_access_token(data={"sub": user_data.username})
        
        return {"access_token": token, "token_type": "bearer", "username": user_data.username}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error logging in: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/update-score")
async def update_score(score_data: ScoreUpdate, request: Request):
    """Update user's Flappy Bird high score and game count"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        username = auth.verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get current user data
        current_user = await db.db.users.find_one({"username": username})
        current_total_games = current_user.get("total_games", 0)
        
        # Calculate new average score
        new_avg_score = ((current_user.get("avg_score", 0) * current_total_games) + score_data.score) / (current_total_games + 1)
        
        # Update user stats
        result = await db.db.users.update_one(
            {"username": username},
            {
                "$inc": {"total_games": 1},
                "$max": {"high_score": score_data.score},
                "$set": {"avg_score": round(new_avg_score, 2)}
            }
        )
        
        if result.modified_count == 0 and result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated user data
        updated_user = await db.db.users.find_one({"username": username})
        
        return {
            "message": "Score updated successfully",
            "high_score": updated_user.get("high_score", 0),
            "total_games": updated_user.get("total_games", 0),
            "avg_score": updated_user.get("avg_score", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating score: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/update-parkour-score")
async def update_parkour_score(request: Request):
    """Update parkour game score"""
    try:
        data = await request.json()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        username = auth.verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        score = data.get("score", 0)
        
        # Update user's parkour score
        result = await db.db.users.update_one(
            {"username": username},
            {"$max": {"parkour_score": score}}
        )
        
        user = await db.db.users.find_one({"username": username})
        
        return {
            "message": "Score updated successfully",
            "high_score": user.get("parkour_score", 0)
        }
    except Exception as e:
        print(f"Error updating parkour score: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/logout")
async def logout():
    """Logout user"""
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("access_token")
    return response

# ==================== LEADERBOARD ENDPOINTS ====================

@app.get("/api/leaderboard")
async def get_flappy_leaderboard():
    """Get top 10 scores for Flappy Bird"""
    try:
        leaderboard = await db.db.users.find(
            {}, 
            {"username": 1, "high_score": 1, "_id": 0}
        ).sort("high_score", -1).limit(10).to_list(None)
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        print(f"Error getting flappy leaderboard: {e}")
        return {"leaderboard": []}

@app.get("/api/parkour-leaderboard")
async def get_parkour_leaderboard():
    """Get top 10 scores for Parkour game"""
    try:
        leaderboard = await db.db.users.find(
            {}, 
            {"username": 1, "parkour_score": 1, "_id": 0}
        ).sort("parkour_score", -1).limit(10).to_list(None)
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        print(f"Error getting parkour leaderboard: {e}")
        return {"leaderboard": []}

# ==================== GAMEPLAY STATS ENDPOINTS ====================

@app.get("/api/get-gameplay-stats")
async def get_gameplay_stats(request: Request):
    """Get gameplay statistics for graph"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            return {"gameplayData": [], "bestLevel": 1, "avgScore": 0}
        
        username = auth.verify_token(token)
        if not username:
            return {"gameplayData": [], "bestLevel": 1, "avgScore": 0}
        
        # Get user data
        user = await db.db.users.find_one({"username": username})
        
        # Try to get gameplay data from separate collection
        gameplay_records = await db.db.gameplay.find(
            {"username": username}
        ).sort("timestamp", -1).limit(10).to_list(None)
        
        gameplayData = []
        for record in gameplay_records:
            if record.get("gameplayData"):
                gameplayData.extend(record.get("gameplayData", []))
        
        # Sort by time
        gameplayData.sort(key=lambda x: x.get('time', 0))
        
        return {
            "gameplayData": gameplayData,
            "bestLevel": user.get("best_level", 1) if user else 1,
            "avgScore": user.get("avg_score", 0) if user else 0
        }
    except Exception as e:
        print(f"Error getting gameplay stats: {e}")
        return {"gameplayData": [], "bestLevel": 1, "avgScore": 0}

@app.post("/api/save-gameplay")
async def save_gameplay(request: Request):
    """Save gameplay data for graph"""
    try:
        data = await request.json()
        token = request.cookies.get("access_token")
        if not token:
            return {"error": "Not authenticated"}
        
        username = auth.verify_token(token)
        if not username:
            return {"error": "Invalid token"}
        
        # Update user's best level
        finalLevel = data.get("finalLevel", 1)
        await db.db.users.update_one(
            {"username": username},
            {"$max": {"best_level": finalLevel}}
        )
        
        # Store gameplay data
        gameplay_record = {
            "username": username,
            "finalScore": data.get("finalScore", 0),
            "finalLevel": finalLevel,
            "pipesPassed": data.get("pipesPassed", 0),
            "gameplayData": data.get("gameplayData", []),
            "timestamp": get_current_time()
        }
        
        # Store in gameplay collection (create if doesn't exist)
        try:
            await db.db.gameplay.insert_one(gameplay_record)
        except:
            # If collection doesn't exist, create it
            await db.db.create_collection("gameplay")
            await db.db.gameplay.insert_one(gameplay_record)
        
        # Keep only last 10 records per user
        all_records = await db.db.gameplay.find({"username": username}).sort("timestamp", -1).to_list(None)
        if len(all_records) > 10:
            for record in all_records[10:]:
                await db.db.gameplay.delete_one({"_id": record["_id"]})
        
        return {"message": "Gameplay data saved"}
    except Exception as e:
        print(f"Error saving gameplay: {e}")
        return {"error": str(e)}

# ==================== USER STATS ENDPOINT ====================

@app.get("/api/user/{username}")
async def get_user_stats(username: str):
    """Get user statistics"""
    try:
        user = await db.db.users.find_one(
            {"username": username},
            {"password": 0, "_id": 0}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "games": ["Flappy Bird", "3D Parkour Runner"],
        "database": "connected" if db.db is not None else "disconnected"
    }