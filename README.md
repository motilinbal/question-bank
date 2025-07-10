# DocuMedica - Medical Question Bank Viewer

![DocuMedica Banner](https://i.imgur.com/placeholder.png) <!-- Placeholder for a real banner -->

**DocuMedica** is a standalone, local-first Python application for managing and viewing a medical question bank. It provides a clean, fast, and interactive web interface powered by Streamlit, with a robust backend that uses MongoDB for data storage.

---

## ✨ Key Features

* **Advanced Filtering**: Search and filter questions by text, source, tags, favorites, and review status.
* **Interactive Question Viewer**: View questions with rich media (images, videos), explanations, and choices in a clean, readable format.
* **Personalization**: Mark questions as favorites, flag them for review, and add personal notes.
* **Local-First**: Runs entirely on your local machine, ensuring your data remains private and accessible offline.
* **Data Ingestion**: Includes a service to easily import questions from a structured JSON format.
* **Modern & Robust**: Built with modern tools like Pydantic for data validation and a layered architecture for maintainability.

---

## 📸 Screenshots

| Question List View                               | Detailed Question View                            |
| ------------------------------------------------ | ------------------------------------------------- |
| ![List View](https://i.imgur.com/placeholder.png) | ![Detail View](https://i.imgur.com/placeholder.png) |

<!-- Placeholder for real screenshots -->

---

## 🛠️ Tech Stack

* **Backend**: Python
* **Frontend/UI**: Streamlit
* **Database**: MongoDB
* **Data Validation**: Pydantic
* **Configuration**: Pydantic-Settings
* **Testing**: Pytest, Pytest-mock
* **Code Quality**: Black, Flake8

---

## 🚀 Getting Started

Follow these instructions to set up and run the project on your local machine.

### Prerequisites

* Python 3.9+
* A running instance of MongoDB. You can run it locally or use a free cloud instance (e.g., from MongoDB Atlas).
* Git

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/documedica.git](https://github.com/your-username/documedica.git)
    cd documedica
    ```

2.  **Create and Activate a Virtual Environment**
    This project is designed to run in a dedicated virtual environment to manage dependencies.
    ```bash
    # Create the virtual environment (named 'venv')
    python3 -m venv venv

    # Activate it on macOS/Linux
    source venv/bin/activate

    # Or, activate it on Windows (Command Prompt)
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**
    Install all required Python packages.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    The application uses a `.env` file to manage configuration, especially database credentials.
    * Create a file named `.env` in the root of the project directory.
    * Add your configuration details to it. You can use the example below as a template.

    **.env file:**
    ```env
    # Your MongoDB connection string
    MONGO_URI="mongodb://localhost:27017/"

    # The name of the database to use
    MONGO_DB_NAME="question_bank"

    # The name of the main questions collection
    MONGO_COLLECTION_NAME="questions"
    ```

5.  **Import Sample Data (Optional)**
    To populate your database with initial data, you can run the ingestion script.
    ```bash
    # Make sure your .env file is configured correctly first
    python -m scripts.import_data sample_import.json
    ```
    *(Note: The script path might vary; adjust as needed based on project structure.)*

6.  **Run the Application**
    Launch the Streamlit web server.
    ```bash
    streamlit run main.py
    ```
    The application should now be open and accessible in your default web browser!

---

## 📂 Project Structure

The project follows a layered architecture to ensure a clean separation of concerns.

.├── assets/             # Static media files (images, videos)
│   └── ...
├── docs/               # Detailed documentation files
│   └── technical_overview.md
├── scripts/            # Helper scripts (e.g., data importer)
│   └── ...
├── tests/              # Unit and integration tests
│   └── ...
├── config.py           # Application configuration loader
├── database.py         # Data Access Layer (MongoDB singleton)
├── main.py             # UI Layer (Streamlit application)
├── models.py           # Data Modeling Layer (Pydantic models)
├── README.md           # This file
├── requirements.txt    # Application dependencies
├── services.py         # Business logic for the new schema
├── updated_legacy_adapter.py # Adapter for legacy DB schema
└── updated_question_service.py # Business logic used by the UI
---

## ✅ Testing & Quality

To ensure the reliability of the application, we use `pytest` for testing and `black`/`flake8` for code quality.

1.  **Install Development Dependencies**
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Run Tests**
    Execute the full test suite:
    ```bash
    pytest
    ```

3.  **Check Code Quality**
    ```bash
    # Format code with Black
    black .

    # Lint code with Flake8
    flake8 .
    ```

---

## 📖 Further Documentation

For a deep dive into the application's architecture, data flow, and design decisions, please see the **[Comprehensive Technical Guide](./docs/technical_overview.md)**.