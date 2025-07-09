# Refactoring: A Master Plan

## 1. Introduction

This document outlines the master plan for the complete refactoring of the **DocuMedica** application. The primary objective is to create a **standalone, local Python application** that retains all the core functionalities of the original system, with the exception of vector-based search.

The new implementation will be guided by the principles of **simplicity, robustness, and efficiency**. We will move away from the client-server architecture and create a unified application that is easy to install, use, and maintain.

## 2. Core Philosophy

* **Lean and Mean**: The application should have a minimal footprint. We will use a curated set of libraries and avoid unnecessary complexity. The code should be concise and expressive.
* **Robustness First**: The application must be reliable. We will incorporate comprehensive error handling and data validation to ensure stability.
* **Modern and Elegant**: We will leverage modern Python features and best practices to create a clean, readable, and maintainable codebase.
* **User-Centric Design**: While we are eliminating the web frontend, the user experience remains a priority. The application should be intuitive and easy to navigate.

## 3. System Architecture

The new application will be a single, monolithic application with a clear separation of concerns. The proposed architecture is as follows:

* **Main Application (`main.py`)**: The entry point of the application. It will handle command-line arguments and orchestrate the different components.
* **User Interface (UI)**: We will use **Streamlit** to create a simple and interactive web-based UI. This will allow us to easily display questions, media, and other information to the user in their browser without the need for a separate frontend.
* **Data Access Layer (`database.py`)**: This module will be responsible for all interactions with the **MongoDB** database. It will contain functions for querying, inserting, updating, and deleting documents.
* **Services Layer (`services.py`)**: This layer will contain the core business logic of the application. It will include functions for:
    * **Question Management**: Creating, retrieving, and updating questions.
    * **Media Management**: Handling images, videos, and other media files.
    * **Data Ingestion**: Processing and importing new questions and data.
* **Models (`models.py`)**: This module will define the data structures for all the entities in the system, using **Pydantic** for data validation and serialization.

## 4. MongoDB Database Schema

The MongoDB database will be the single source of truth for all data in the application. We will use a clear and concise schema to ensure data consistency and integrity.

The database will have three main collections:

1.  **`questions`**: This collection will store all the information related to each question.

    ```json
    {
      "_id": "<ObjectId>",
      "question_id": "<string> (unique identifier)",
      "text": "<string> (the question text in HTML format)",
      "source": "<string> (e.g., 'uworld', 'amboss')",
      "tags": ["<string>", "<string>", ...],
      "is_marked": "<boolean>",
      "is_favorite": "<boolean>",
      "notes": "<string>",
      "media": [
        {
          "media_id": "<string> (references the 'media' collection)",
          "type": "<string> (e.g., 'image', 'video', 'page')",
          "placeholder": "<string> (a unique placeholder in the question text)"
        }
      ],
      "created_at": "<ISODate>",
      "updated_at": "<ISODate>"
    }
    ```

2.  **`media`**: This collection will store metadata about each media file.

    ```json
    {
      "_id": "<ObjectId>",
      "media_id": "<string> (unique identifier)",
      "type": "<string> (e.g., 'image', 'video', 'page')",
      "path": "<string> (the relative path to the media file)",
      "description": "<string>",
      "created_at": "<ISODate>"
    }
    ```

3.  **`sources`**: This collection will store information about the different question sources.

    ```json
    {
      "_id": "<ObjectId>",
      "name": "<string> (e.g., 'uworld', 'amboss')",
      "description": "<string>",
      "url": "<string>"
    }
    ```

## 5. Asset Management

All media files (images, videos, etc.) will be stored in a local directory structure. The `media` collection in MongoDB will store the relative paths to these files.

The proposed directory structure is as follows:

````

/
|-- assets/
|   |-- images/
|   |-- videos/
|   |-- audio/
|-- main.py
|-- database.py
|-- services.py
|-- models.py

```

When a question is rendered, the application will read the `media` array in the question document. For each media item, it will retrieve the corresponding media document from the `media` collection and use the `path` to load the media file from the `assets` directory. The media will then be embedded in the question's HTML using the `placeholder`.

## 6. Data Flow and Logic

The core data flow of the application will be as follows:

1.  **Data Ingestion**:
    * The `services.py` module will contain a function to ingest new data from various sources.
    * This function will parse the data, create `Question` and `Media` objects using the Pydantic models, and save them to the MongoDB database.
    * Media files will be saved to the appropriate subdirectory in the `assets` directory.

2.  **Question Retrieval**:
    * The user will use the Streamlit UI to search for questions.
    * The UI will provide filters for `source`, `tags`, `is_marked`, and `is_favorite`.
    * The `database.py` module will contain a function to query the `questions` collection based on the user's filters.

3.  **Question Rendering**:
    * Once a question is selected, the application will retrieve the full question document from the database.
    * It will then iterate through the `media` array and fetch the corresponding media files.
    * The application will replace the placeholders in the question's HTML with the actual media content.
    * The final HTML will be rendered in the Streamlit UI.

4.  **Marking and Favoriting**:
    * The user will be able to mark or favorite questions through the UI.
    * These actions will trigger an update to the `is_marked` or `is_favorite` field in the corresponding question document in the database.

## 7. Development Roadmap

The development process will be divided into the following phases:

1.  **Phase 1: Setup and Foundation**
    * Set up the project structure.
    * Initialize the MongoDB database.
    * Implement the Pydantic models.
    * Implement the `database.py` module with basic CRUD operations.

2.  **Phase 2: Data Ingestion**
    * Implement the data ingestion service in `services.py`.
    * Write scripts to migrate the data from the old system to the new database schema.

3.  **Phase 3: Core Application Logic**
    * Implement the question retrieval and rendering logic in `services.py`.
    * Implement the marking and favoriting functionality.

4.  **Phase 4: User Interface**
    * Develop the Streamlit UI for searching, filtering, and displaying questions.
    * Integrate the UI with the backend services.

5.  **Phase 5: Testing and Refinement**
    * Write unit and integration tests for all components.
    * Perform thorough testing of the entire application.
    * Refine the UI and add any final touches.

By following this master plan, we can ensure a smooth and efficient development process, resulting in a high-quality, robust, and modern application.