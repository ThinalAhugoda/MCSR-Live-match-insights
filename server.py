from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from OverlayState import overlay
from fastapi.templating import Jinja2Templates
from ESP_app import app as esp_app
import requests
import os
from pathlib import Path



app = FastAPI(title="MCSR Insights API")
templates = Jinja2Templates(directory="Templates")

# Mount static files (CSS, images, etc.)
app.mount("/static", StaticFiles(directory="Style"), name="style")

# Allowing overlay webpage to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions for fetching player skins
def get_player_uuid(username: str) -> str | None:
    """Fetch player UUID from Mojang API"""
    try:
        response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}")
        if response.status_code == 200:
            data = response.json()
            return data.get("id")
        else:
            print(f"Error fetching UUID for {username}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching UUID for {username}: {e}")
        return None

def get_and_save_player_skin(username: str) -> bool:
    """Fetch player skin from mineatar.io and save to Style/players folder"""
    try:
        # Get UUID from Mojang API
        uuid = get_player_uuid(username)
        if not uuid:
            print(f"Could not get UUID for {username}")
            return False
        
        # Create players directory if it doesn't exist
        players_dir = Path("Style/players")
        players_dir.mkdir(parents=True, exist_ok=True)
        
        # File path for the skin
        skin_path = players_dir / f"{username.lower()}.png"
        
        # Skip if already cached
        if skin_path.exists():
            print(f"Skin already cached for {username}")
            return True
        
        # Fetch skin from mineatar.io
        skin_url = f"https://api.mineatar.io/face/{uuid}?scale=4&overlay=true&format=png"
        response = requests.get(skin_url)
        
        if response.status_code == 200:
            # Save the image
            with open(skin_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully saved skin for {username} to {skin_path}")
            return True
        else:
            print(f"Error fetching skin for {username}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Exception fetching skin for {username}: {e}")
        return False

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    context = {"request": request, "title": "My FastAPI Site", "message": "Hello World!"}
    return templates.TemplateResponse("index.html", context)

@app.get("/ESP")
def run_prediction():
    esp_app()
    return RedirectResponse(url="/overlay")

@app.get("/overlay", response_class=HTMLResponse)
def get_overlay(request: Request):
    overlay_data = overlay.get()
    
    # Fetch and cache player skins before rendering
    if overlay_data.get("visible") and overlay_data.get("players"):
        for player in overlay_data["players"]:
            player_name = player.get("name")
            if player_name:
                print(f"Fetching skin for player: {player_name}")
                get_and_save_player_skin(player_name)
    
    context = {"request": request, "overlay": overlay_data}
    return templates.TemplateResponse("ESP_graphic.html", context)