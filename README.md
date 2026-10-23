
# OpenHospitalFlow

**An open-source hospital workflow and analytics project built with Python.**

OpenHospitalFlow is an educational web application that demonstrates how a Kanban workflow board and basic analytics can be combined to track fictional hospital visits.

## Features

- Register and track fictional patient visits.
- Manage six workflow stages: Registered, Waiting, Consultation, Diagnostics, Treatment, and Discharged.
- Record status-change timestamps and view visit history.
- Display workflow and department charts.
- Calculate recorded waiting times and completed visit durations.
- Generate fictional demo records.
- Run automated tests using pytest.

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Plotly
- pytest
- HTML and CSS

## Requirements

- Python 3.10 or newer
- Git (optional for running locally, required for Git-based collaboration)

## Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd OpenHospitalFlow
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your repository's actual URL.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Run the application

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

### 4. Generate demo data

Stop the server, then run:

```bash
python generate_demo_data.py
```

The generator creates fictional visits and avoids adding the same demo dataset twice.

### 5. Run automated tests

```bash
python -m pytest -v
```

## Project Structure

```text
OpenHospitalFlow/
├── app.py
├── generate_demo_data.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── tests/
    └── test_app.py
```

## Privacy and Safety

This project is for educational demonstration only. Use fictional data exclusively. It is not designed or validated for clinical decisions or production healthcare operations.

## Future Improvements

- Search and filter visits.
- Department-specific workflow limits.
- Export analytics reports.
- Improve validation and automated test coverage.
- Add user authentication and access controls.
- Add a more detailed analytics dashboard.

## License

Released under the MIT License. See `LICENSE` for details.
