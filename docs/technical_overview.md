# DocuMedica Application: A Comprehensive Technical Guide

## 1. Introduction & Core Philosophy

This document provides a comprehensive technical overview of the **DocuMedica** application, a standalone, local Python application designed for managing and viewing a medical question bank. The goal of this document is to provide any developer with the deep knowledge required to understand, maintain, and extend the project from scratch.

The application is built on a philosophy of **simplicity, robustness, and efficiency**.

* **Lean and Mean**: It uses a curated set of libraries to maintain a minimal footprint and avoid unnecessary complexity. The dependencies are managed in `requirements.txt` for the application and `requirements-dev.txt` for development tools.
* **Robustness First**: The application incorporates comprehensive data validation via Pydantic models and a structured, layered architecture to ensure stability and reliability.
* **Modern and Elegant**: The codebase leverages modern Python features and best practices to be clean, readable, and maintainable. Code quality is enforced using `black` for formatting and `flake8` for linting.
* **User-Centric Design**: The user experience is prioritized through a simple and interactive web-based UI powered by Streamlit, making the application intuitive to navigate.

---

## 2. System Architecture

The application follows a monolithic architecture with a clear separation of concerns, ensuring that each component has a distinct and well-defined responsibility. The entire project is designed to run within a Python virtual environment, which should be created in the project root and is typically named `venv`.

![System Architecture Diagram](https://i.imgur.com/example.png) <!-- Placeholder for a real diagram -->

### Core Components:

* **`main.py` (UI Layer)**
    * **Responsibility**: This is the main entry point for the application. It uses the **Streamlit** library to create the entire web-based user interface.
    * **Logic**: It initializes the page configuration and session state to manage user interactions (e.g., tracking the selected question). It defines the UI layout, including a sidebar for search and filtering controls and a main content area for displaying data. It acts as a router, deciding whether to display the list of questions or a detailed view of a single question based on the session state (`st.session_state.selected_question_id`). It fetches filter options (sources, tags) from the database via the adapter and populates the sidebar widgets. Finally, it handles user interactions (button clicks, text input) and calls the appropriate service layer functions in response.

* **`database.py` (Data Access Layer)**
    * **Responsibility**: This module is the sole component responsible for all interactions with the **MongoDB** database. It abstracts away low-level `pymongo` calls into a clean, reusable interface.
    * **Logic**: It is implemented as a **singleton** to ensure only one database connection is active across the application, preventing resource leaks. It establishes a connection to the MongoDB server using connection details from `config.py`. It provides basic **CRUD** (Create, Read, Update, Delete) methods and handles the conversion between string IDs and MongoDB's `ObjectId` type.

* **`updated_question_service.py` & `services.py` (Service/Business Logic Layer)**
    * **Responsibility**: This layer contains the core business logic, orchestrating data flow between the UI (`main.py`) and the adapter layer.
    * **`updated_question_service.py`**: This is the service actively used by the Streamlit UI. The `UpdatedQuestionService` is a lean service that interfaces with the `UpdatedLegacyAdapter`. It is responsible for rendering the final HTML for a question (including choices and explanations) and handling state changes like toggling favorites or updating notes.
    * **`services.py`**: This file contains the logic for a *new, refactored* data schema, which is not currently in use by the main UI but is available for future migrations. The `IngestionService` handles importing data from a structured JSON file (`sample_import.json`), while the `QuestionService` contains logic for managing questions based on the *new* schema.

* **`updated_legacy_adapter.py` (Adapter Layer)**
    * **Responsibility**: This is a critical component that acts as a bridge between the new Pydantic data models (`models.py`) and the actual, pre-existing ("legacy") database schema. It allows the modern application logic to work with the old data structure without requiring an immediate, large-scale data migration.
    * **Logic**: It maps modern query fields (e.g., `is_favorite`) to their legacy database equivalents (e.g., `flagged`). It translates UI search queries into legacy-compatible MongoDB queries (e.g., using `$text` for full-text search). It fetches raw documents and transforms them into the new `Question`, `Choice`, and `ImageSet` Pydantic models, handling inconsistencies in the legacy data (like different formats for choices). It also provides methods like `get_sources()` and `get_tags()` by running aggregation pipelines on the database.

* **`models.py` (Data Modeling Layer)**
    * **Responsibility**: Defines the ideal data structures for all entities using **Pydantic**. These models are the "single source of truth" for what the application's data *should* look like.
    * **Logic**: It uses Pydantic's `BaseModel` to define robust, self-validating data classes like `Question`, `Choice`, and `ImageSet`. It uses `Field` for aliasing (e.g., mapping a database `_id` to a model's `question_id`) and setting defaults. This enforces strict data types, preventing bugs by ensuring data conforms to the schema.

* **`config.py` (Configuration)**
    * **Responsibility**: Manages all application settings in a central, secure, and flexible way.
    * **Logic**: It uses `pydantic-settings` to load sensitive configuration (like database URIs) from a `.env` file, keeping secrets out of the codebase. It defines a `Settings` class that holds all configuration variables, preventing the use of "magic strings".

---

## 3. Database Schema

The application is designed to work with a MongoDB database. A key architectural point is that the `updated_legacy_adapter.py` allows the application to operate on a *legacy* schema while the Pydantic models in `models.py` define the *target* schema.

### Collections:

1.  **`questions` Collection** (Legacy Name)
    * This is the primary collection storing all question data. The adapter's job is to make the raw documents from this collection look like the `Question` model to the rest of the application.
    * **Key Legacy Fields (and their modern mapping)**:
        * `_id`: MongoDB's unique `ObjectId`, mapped to `question_id`.
        * `name`: The title of the question.
        * `source`: The origin of the question (e.g., "UWorld").
        * `tags`: A list of strings for categorization.
        * `images`: A dictionary containing image IDs, mapped to the `ImageSet` model.
        * `question`: HTML content of the question, mapped to `question_html`.
        * `explanation`: HTML content for the explanation, mapped to `explanation_html`.
        * `choices`: A list that can contain either strings or dictionaries, which the adapter normalizes into a list of `Choice` objects.
        * `flagged`: A boolean, mapped to `is_favorite`.
        * `difficult`: A boolean, mapped to `is_marked` for filtering and `difficult` on the model.
        * `notes`: A string for user-added notes.

2.  **`images` Collection** (Legacy Name for Media)
    * Stores metadata about media files. The `IngestionService` maps this to the `MediaItem` model during the import process described in `services.py`.
    * **Schema Fields**: `media_id`, `type`, `path` (relative path in `assets`), `content` (for HTML pages), `description`.

3.  **`sources` Collection**
    * Stores information about the different question sources.
    * **Schema Fields**: `name`, `description`, `url`.

---

## 4. Asset Management

All static media files are stored locally in a structured `assets/` directory. The MongoDB `images` collection does not store the files themselves but rather the metadata and the relative path to them.

* **Directory Structure**:
    ```
    /
    |-- assets/
    |   |-- images/
    |   |-- videos/
    |   |-- audio/
    ```
* When a media item is ingested, the `IngestionService` in `services.py` copies the source file into the appropriate subdirectory (e.g., an image goes into `assets/images/`). It then stores the new relative path (e.g., `images/ecg-456.jpg`) in the `MediaItem` document in the database.
* When a question is rendered, the `UpdatedQuestionService` constructs the final HTML, which may contain `<img>` or `<video>` tags. The `src` attribute of these tags points to the file paths within the `assets` directory, which Streamlit serves to the user's browser.

---

## 5. Data Flow and Logic

### Data Ingestion (New Schema)

This flow, defined in `services.py`, is for populating a database that follows the new, clean schema defined in `models.py`. It is not used by the main application but is a utility for setup.

1.  A JSON file (like `sample_import.json`) is provided.
2.  The `IngestionService.import_from_json` method is called.
3.  The service first calls `get_or_create_source` to find or create the source document in MongoDB.
4.  It then iterates through each question in the JSON. For each question, it processes the associated media:
    * `process_media_item` checks if the media already exists in the `images` collection.
    * If it's a file (`image`, `video`), it's copied to the `assets` directory.
    * A new `MediaItem` document is created in the database.
5.  Finally, a new `Question` document is created in the `questions` collection, linking to the source and media.

### Question Retrieval and Display (Live Flow)

This is the primary data flow for the interactive application, which uses the adapter to work with the legacy schema.

1.  **User Applies Filters**: The user interacts with the sidebar widgets in the Streamlit UI (`main.py`).
2.  **Query Construction**: A `query` dictionary is built dynamically in `main.py` based on the user's selections (search text, sources, tags, etc.).
3.  **Adapter Call**: The `updated_legacy_adapter.find_questions_paginated` method is called with the query and pagination details.
4.  **Database Query**: The adapter translates the UI query into a legacy-compatible MongoDB aggregation pipeline and fetches the raw documents from the database via the `database.py` singleton.
5.  **Data Transformation**: The adapter parses each raw document, transforming it into a valid `Question` Pydantic model. This is the most complex step, involving field mapping and data cleaning (e.g., normalizing the `choices` field).
6.  **UI Display**: The list of `Question` objects is returned to `main.py`, which then displays a summary of each question in a clickable list.
7.  **Detailed View**: When the user clicks "View Details" on a question:
    * The `selected_question_id` is set in the session state, and Streamlit re-runs the script.
    * The app now routes to the `display_question_detail` function.
    * `updated_question_service.get_question_by_id` is called, which again uses the adapter to fetch the full question data.
    * `updated_question_service.render_question_html` is called to generate the final HTML for the question, choices, and explanation.
    * This HTML is rendered in the browser using `st.markdown(..., unsafe_allow_html=True)`.

### User Interactions (Favoriting, Notes)

1.  In the detailed view, the user clicks a button like "Favorite ⭐".
2.  The `on_click` handler in `main.py` calls the corresponding method in the service, e.g., `question_service.toggle_favorite(q_id)`.
3.  The `UpdatedQuestionService` method calls the adapter's `update_question_field` method.
4.  The adapter maps the modern field name (`is_favorite`) to the legacy one (`flagged`) and constructs an update operation for MongoDB.
5.  The `db_client.update_one` method executes the change in the database.
6.  Streamlit re-runs the script, re-fetching the data and displaying the updated state (e.g., the button now shows "Unfavorite ⭐").

---

## 6. Testing and Quality Assurance

The project emphasizes quality through a structured testing and linting process, as outlined in `phase4.md` and the `tests/` directory.

* **Unit Testing**:
    * The `pytest` framework is used for writing and running tests, with dependencies managed in `requirements-dev.txt`.
    * `pytest-mock` is used extensively to isolate tests from the live database and filesystem. For example, `test_database.py` mocks `pymongo.MongoClient`, and `test_services.py` mocks the `db_client`.
* **Code Quality**:
    * **`black`**: Used to enforce a consistent, automatic code formatting style.
    * **`flake8`**: Used as a linter to identify potential bugs, stylistic errors, and overly complex code.

---

## 7. How to Build from Scratch (A Developer's Guide)

This section outlines the steps to build this application, synthesizing the project's phase-based development plan.

**Phase 1: Foundation and Data Layer**
1.  **Project Setup**: Create the directory structure (`assets/`, `tests/`) and empty Python files (`main.py`, `database.py`, `models.py`, `services.py`, `config.py`). Set up a `.gitignore` file.
2.  **Configuration (`config.py`)**: Implement `config.py` to load database URI and name from a `.env` file using `pydantic-settings`.
3.  **Data Modeling (`models.py`)**: Implement the `Question`, `MediaItem`, `Source`, `Choice`, and `ImageSet` Pydantic models. Pay close attention to field aliasing (`alias="_id"`) and data types to define the ideal state of your data.
4.  **Database Singleton (`database.py`)**: Implement the `Database` class as a singleton to manage a single, persistent connection to MongoDB. Implement the core CRUD methods, ensuring they handle `ObjectId` conversion.

**Phase 2: Business Logic and Data Ingestion**
1.  **Ingestion Service (`services.py`)**: Create the `IngestionService`. Implement the logic to `get_or_create_source`, `process_media_item` (including copying files to the `assets` directory), and the main `import_from_json` orchestrator function. Create a `sample_import.json` to test against.
2.  **Question Service (`services.py`)**: Implement the `QuestionService` with methods like `get_question_by_id`, `render_question_html`, and state-management functions. This service will initially be built assuming the *ideal* schema.

**Phase 3: Building the Interactive UI**
1.  **Adapter for Legacy Data (`updated_legacy_adapter.py`)**: This is where you bridge the gap. Create the `UpdatedLegacyAdapter`. Write the methods to translate modern queries into legacy queries, fetch raw data, and meticulously parse it into the Pydantic models you defined in Phase 1.
2.  **Refined Service (`updated_question_service.py`)**: Create the `UpdatedQuestionService` that uses the adapter instead of calling the database directly. This service will be used by the UI.
3.  **Streamlit UI (`main.py`)**:
    * Set up the basic page layout (`st.set_page_config`) and session state (`st.session_state`).
    * Create the sidebar with filter widgets (`st.text_input`, `st.multiselect`). Fetch filter options using the adapter.
    * Implement `display_question_list`: Build the query dict from the filters, call the adapter's paginated find method, and render the results in a loop, with a "View Details" button for each.
    * Implement `display_question_detail`: Fetch the full question using the service, render its HTML, and add interactive buttons (Back, Favorite, Notes) that call the service methods.

**Phase 4: Quality and Finalization**
1.  **Testing (`tests/`)**: Write unit tests using `pytest` and `pytest-mock`. Create `test_database.py` and `test_services.py`. Mock all external dependencies like the database and filesystem to ensure tests are fast and isolated.
2.  **Code Quality**: Run `black .` and `flake8 .` on the entire codebase to format and lint it.
3.  **Documentation**: Write comprehensive docstrings for all modules and functions. Create a `README.md` with instructions on setup and usage.
4.  **Dependencies**: Finalize `requirements.txt` and `requirements-dev.txt` to lock down the exact versions of all packages used.
