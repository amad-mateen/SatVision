# Flood Segmentation Frontend

Real-time flood detection using satellite imagery with an interactive Leaflet map interface.

## Features

- **Interactive Map**: Pan across satellite imagery at a fixed zoom level (13) for consistent Sentinel-2 resolution
- **Flood Detection**: Click "Detect Floods" to trigger the backend inference
- **Live Overlay**: View U-Net++ segmentation results overlaid on the map at 60% opacity
- **Error Handling**: User-friendly error messages for API failures
- **Processing State**: Visual feedback during satellite data processing

## Installation

### Prerequisites
- Node.js (v14+) and npm
- Backend API running on `http://localhost:5000`

### Setup

```bash
cd frontend
npm install
```

## Running the Application

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000).

## Backend Integration

The frontend expects a Flask backend API endpoint at:
```
POST http://localhost:5000/api/detect
```

**Request Body:**
```json
{
  "bbox": {
    "north": 30.5,
    "south": 30.2,
    "east": 69.5,
    "west": 69.2
  },
  "zoom": 13
}
```

**Expected Response:**
```json
{
  "mask_url": "data:image/png;base64,..." or "https://..."
}
```

The backend should:
1. Fetch current satellite imagery via Copernicus/Sentinel Hub
2. Fetch historical imagery (30 days prior)
3. Run U-Net++ inference on the satellite bands
4. Return the binary water/flood mask as PNG (Base64 or URL)

## Configuration

Edit `src/App.js` to modify:
- **LOCKED_ZOOM_LEVEL**: Fixed zoom level (default: 13 for ~19m/pixel)
- **SATELLITE_TILE_URL**: Tile provider (default: Esri World Imagery)
- **Default Position**: Initial map center (default: Central Pakistan [30.3753, 69.3451])
- **Backend API URL**: Change `http://localhost:5000/api/detect` as needed

## Technologies Used

- **React 18**: UI framework
- **React-Leaflet 4**: Map integration
- **Leaflet**: JavaScript mapping library
- **Axios**: HTTP client
- **Esri World Imagery**: Satellite tile layer

## License

This project is part of the Flood Segmentation research initiative.
