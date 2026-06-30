# Flood Segmentation Frontend

This directory contains the React frontend for the flood segmentation satellite imagery project.

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

The app will automatically open in your browser at `http://localhost:3000`.

## Project Structure

```
frontend/
├── public/
│   └── index.html           # Main HTML file
├── src/
│   ├── App.js               # Main React component with map and detection logic
│   └── index.js             # React DOM root
├── package.json             # Dependencies and scripts
└── README.md                # Full documentation
```

## Backend Configuration

Make sure your Flask backend is running on `http://localhost:5000` with the endpoint:
- `POST /api/detect` - Accepts bbox and zoom, returns mask_url

## Features

- Interactive satellite map centered on Pakistan
- Real-time flood detection overlay
- Processing state with visual feedback
- Error handling with user messages
- Fixed zoom level for consistent resolution

## Notes

- The map uses Esri World Imagery for high-quality satellite tiles
- Zoom is locked at level 13 (~19m/pixel at equator) for Sentinel-2 consistency
- Results overlay is semi-transparent (60% opacity) to see terrain underneath
