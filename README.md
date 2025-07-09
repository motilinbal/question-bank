# DocuMedica Refactored

A lean, robust, and modern standalone Python application for managing and viewing a medical question bank. This project uses MongoDB for data storage and Streamlit for the user interface.

## ✨ Features

-   **Advanced Filtering**: Search questions by text, source, and tags.
-   **Question Management**: Mark questions as favorite, flag them for review, and add personal notes.
-   **Rich Media Support**: View questions with embedded images, videos, audio, and formatted text pages.
-   **Data Ingestion**: A powerful service to import new questions from a structured JSON format.
-   **Modern UI**: A clean, fast, and intuitive web-based interface powered by Streamlit.

## ⚙️ Prerequisites

-   Python 3.8+
-   MongoDB Server (running locally or on a cloud service like MongoDB Atlas).

## 🚀 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd documedica_refactored
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use: .\.venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your environment:**
    -   Copy the `.env.example` file to `.env`.
    -   Update the `MONGO_URI` and `DB_NAME` variables in the `.env` file to point to your MongoDB instance.

## 🏃‍♀️ Running the Application

1.  **(First Time Only) Ingest Data:**
    -   Place your data file (e.g., `sample_import.json`) in the project root.
    -   Ensure any local media files are referenced with correct paths inside the JSON.
    -   Run the ingestion script:
        ```python
        from services import IngestionService
        ingestion_service = IngestionService()
        ingestion_service.import_from_json("sample_import.json")
        ```

2.  **Launch the User Interface:**
    ```bash
    streamlit run main.py
    ```
    The application will open automatically in your web browser.

## 📂 Project Structure

```
/
|-- assets/             # For storing media files (images, videos, audio)
|-- tests/              # Unit tests for the application
|-- config.py           # Application configuration loader
|-- database.py         # Handles all MongoDB interactions
|-- main.py             # The main Streamlit application UI
|-- models.py           # Pydantic data models for validation
|-- services.py         # Core business logic (ingestion, question management)
|-- requirements.txt    # Production dependencies
|-- requirements-dev.txt # Development dependencies
|-- README.md           # This file
```

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=.
```

### Code Quality

```bash
# Format code
black .

# Check code quality
flake8 .
```

## 📊 Data Format

The application expects JSON data in the following format:

```json
{
  "source_name": "UWorld",
  "source_description": "A popular question bank for medical students.",
  "questions": [
    {
      "question_id": "uw-med-123",
      "text": "Question text with %%PLACEHOLDER%% for media",
      "tags": ["cardiology", "ecg"],
      "media": [
        {
          "media_id": "uw-ecg-456",
          "type": "image",
          "placeholder": "%%PLACEHOLDER%%",
          "asset_path": "path/to/image.jpg",
          "description": "ECG description"
        }
      ]
    }
  ]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Uses [MongoDB](https://www.mongodb.com/) for data storage
- Powered by [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation