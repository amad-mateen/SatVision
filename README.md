# SatVision 🌊

**SatVision** is a satellite image segmentation tool designed for **post-flood disaster assessment**. It integrates a machine learning backend with an interactive web frontend to detect, segment, and overlay flood water masks from Sentinel-2 satellite imagery in real-time.


## 🔗 Live Deployments

* **Frontend App:** [sat-vision.vercel.app](https://sat-vision.vercel.app)
* **Backend API (Hugging Face Space):** [huggingface.co/spaces/SatVision/App](https://huggingface.co/spaces/SatVision/App)

---

## 📂 Project Structure

This repository is organized into two primary subdirectories:

```text
satvision/
├── backend/                  # Flask backend (U-Net++ segmentation & data sourcing)
│   ├── models/               # Pre-trained ML model checkpoints (.ckpt)
│   ├── src/                  # Inference logic, image fetching, and processing
│   ├── main.py / server.py   # Flask API entrypoints
│   └── Dockerfile            # Container definition for deployment (e.g., Hugging Face Spaces)
│
├── frontend/                 # React frontend (Leaflet mapping interface)
│   ├── public/               # Public assets and index.html
│   ├── src/                  # React components, UI pages, and Leaflet configuration
│   ├── package.json          # Node.js dependencies & scripts
│   └── SETUP.md              # Frontend setup guidelines
│
├── .gitattributes            # Git LFS configurations for model checkpoints
├── .gitignore                # Project-wide Git exclusion rules
├── README.md                 # Root documentation (this file)
└── requirements.txt          # Unified Python dependencies (root-level)
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
   pip install -r ../requirements.txt
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

## ☁️ Hugging Face Space Deployment

The backend is configured to be deployed on Hugging Face Spaces using the Docker SDK. Since the project contains both a frontend and backend, when pushing updates to Hugging Face Spaces:

1. Hugging Face Spaces expects all app code and configuration (including the `Dockerfile` and `requirements.txt`) to be present in the root directory of the Hugging Face repository.
2. If you are using Git subtree or a deployment script to push only the `backend/` subdirectory to Hugging Face:
   * **You must copy the root `requirements.txt` into the `backend/` folder prior to pushing**, so that the Docker image builds successfully on Hugging Face.
   * Example script/command to prepare and deploy:
     ```bash
     # Copy requirements.txt to backend folder
     cp requirements.txt backend/requirements.txt
     
     # Deploy using git subtree push (example)
     git subtree push --prefix backend hf master
     ```

---

## 🛠️ Tech Stack

* **Frontend:** React 18, React-Leaflet 4, Leaflet JS, Axios, Esri World Imagery (satellite tiles)
* **Backend:** Flask, PyTorch, U-Net++, OpenCV, Docker
