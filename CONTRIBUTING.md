# Contributing to SatVision

Thank you for your interest in contributing to SatVision! As a geospatial AI application, we maintain high standards of code quality, performance, and reproducibility.

---

## 🛠️ Development Guidelines

### 1. Code Style & Formatting
* **Python (Backend)**: Follow [PEP 8](https://pep8.org/) coding conventions. Docstrings should follow the Google format. 
* **React (Frontend)**: Use clean, functional components. Keep styling rules decoupled into CSS sheets rather than inline attributes where possible.
* **Logging & Errors**: Do not use raw stdout `print` statements. Route all access, trace, and error metrics through Python's standard `logging` library.

### 2. Environment Verification
Before proposing a change, ensure that:
* The backend server starts up locally:
  ```bash
  cd backend
  python main.py
  ```
* All Python imports resolve without errors.
* No system caching files (`__pycache__/`) are tracked or staged.

---

## 🚀 Submission Process

1. **Fork the Repository**: Create a dedicated feature branch.
2. **Commit Changes**: Use clear, semantic commit messages (e.g., `feat: add custom spectral bands`, `fix: prevent leaflet boundary overflow`).
3. **Submit a Pull Request**: Provide a detailed description of what the change solves and how you verified its functionality.
