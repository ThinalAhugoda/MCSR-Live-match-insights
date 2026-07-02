# Image Sourcing Guide

## How to Add Images

### 1. **Logo Image** 
   - **Location**: `Style/logo.png`
   - **Size**: 80x80 pixels (recommended)
   - **Format**: PNG, JPG, or SVG
   - **Description**: MCSR/project logo displayed in the top-left

### 2. **Sponsor Logo**
   - **Location**: `Style/sponsor.png`
   - **Size**: 120x40 pixels (recommended)
   - **Format**: PNG, JPG, or SVG
   - **Description**: Sponsor branding displayed in the top-right

### 3. **Player Images**
   - **Location**: `Style/players/{playername}.png` (lowercase)
   - **Size**: 120x120 pixels (square)
   - **Format**: PNG, JPG, or SVG
   - **Examples**:
     - `Style/players/infume.png`
     - `Style/players/feinberg.png`
   - **Description**: Individual player skins/portraits

## File Structure
```
MCSR-Live-match-insights/
├── Style/
│   ├── esp_graphic.css
│   ├── logo.jpg                 ← Add your MCSR logo here
│   ├── sponsor.jpg              ← Add sponsor logo here
│   └── players/
│       ├── infume.png
│       ├── feinberg.png
│       └── (add more players as needed)
└── ...
```

## How It Works

- The HTML uses **image tags** with **fallback SVG placeholders**
- If an image file doesn't exist, it will display a placeholder
- Images are served from `/static/` path
- Player images are served from `/static/players/{playername}.png` (converted to lowercase)

## Example: Adding a New Player Image

1. Create a 120x120px image of the player
2. Save it as: `Style/players/playername.png` (use lowercase)
3. The HTML will automatically load it when that player's data is displayed

## Notes
- Keep images optimized for web (under 100KB per image)
- Use consistent image sizes for best display
- PNG format recommended for transparency support
