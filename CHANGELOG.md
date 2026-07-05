# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-07-05
### Added
- **Environmental Boot Audits**: Added startup validators in `backend/src/config.py` that check for missing `EE_CREDENTIALS` and `GEMINI_API_KEY` secrets.
- **Structured Enterprise Logging**: Standardized logs using Python's `logging` library, formatting all prints into datetime-anchored system logs.
- **MIT License**: Added the standard open-source license file.
- **Contributing Guidelines**: Added `CONTRIBUTING.md` outlining project code guidelines and testing workflows.

### Changed
- **Modular Directory Organization**: Consolidated all development modules cleanly within `backend/src/` (configurations, databases, routes, and services blueprints) and `frontend/src/` (components, utilities).
- **Global gitignore rules**: Upgraded `.gitignore` to recursively exclude Python compiler cache files (`**/__pycache__/`) across any directories.

### Removed
- **Redundant Clutter Files**: Deleted monolithic duplicates `backend/server.py`, `frontend/App.js`, and the backup directory `frontend_old/` to simplify project replication.

---

## [1.0.0] - 2026-05-12
### Added
- Initial release of the SatVision satellite assessment tool (FYP submission prototype).
- Multi-spectral water segmentation model checkpoint (U-Net++ U-Net segmenter).
- Google Earth Engine data pipeline for Sentinel-2 (optical) and Sentinel-1 (SAR) composites.
- LLM damage reports compiler and FPDF exporter.
- Leaflet map explorer.
