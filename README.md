# SatVision 🌊

**SatVision** is a satellite image segmentation tool designed for **post-flood disaster assessment**. It integrates a machine learning backend with an interactive web frontend to detect, segment, and overlay flood water masks from Sentinel-2 satellite imagery in real-time.

---

## 📂 Project Structure

This repository is organized into two primary subdirectories:

```text
satvision/
├── backend/                  # Flask backend (U-Net++ segmentation & data sourcing)
│   ├── models/               # Pre-trained ML model checkpoints (.ckpt)
│   ├── src/                  # Inference logic, image fetching, and processing
│   ├── main.py / server.py   # Flask API entrypoints
│   ├── Dockerfile            # Container definition for deployment (e.g., Hugging Face Spaces)
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React frontend (Leaflet mapping interface)
│   ├── public/               # Public assets and index.html
│   ├── src/                  # React components, UI pages, and Leaflet configuration
│   ├── package.json          # Node.js dependencies & scripts
│   └── SETUP.md              # Frontend setup guidelines
│
├── .gitattributes            # Git LFS configurations for model checkpoints
├── .gitignore                # Project-wide Git exclusion rules
└── README.md                 # Root documentation (this file)
```

---

## 🚀 Getting Started

### 1. Backend (Flask & Machine Learning)
The backend manages data fetching from satellite providers (Copernicus / Sentinel Hub) and performs inference using a U-Net++ model to produce flood masks.

#### Prerequisites
* Python 3.8+
* Docker (Optional, if running via container)

#### Local Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the backend server:
   ```bash
   python server.py
   ```
   The backend API will run on `http://localhost:5000`.

---

### 2. Frontend (React & Leaflet Map)
The frontend is a React application that provides a map UI where users can highlight affected regions and trigger real-time flood assessments.

#### Prerequisites
* Node.js (v14+) and npm

#### Local Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm start
   ```
   The application will automatically open in your browser at `http://localhost:3000`.

---

## 📡 API & Integration Details

The React frontend communicates with the Flask backend to request flood masks for a chosen bounding box (bbox) on the map.

### Bounding Box Detection Endpoint
* **Endpoint:** `POST http://localhost:5000/api/detect`
* **Request Format:**
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
* **Response Format:**
  ```json
  {
    "mask_url": "data:image/png;base64,..."
  }
  ```

---

## 🛠️ Tech Stack

* **Frontend:** React 18, React-Leaflet 4, Leaflet JS, Axios, Esri World Imagery (satellite tiles)
* **Backend:** Flask, PyTorch, U-Net++, OpenCV, Docker
