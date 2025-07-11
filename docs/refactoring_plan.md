# Application Refactoring Plan: Database and Service Layer

**Project:** Question Bank Application
**Date:** July 11, 2025
**Author:** Gemini Engineering Intelligence

## 1. Guiding Principles

This refactoring effort will be governed by the following core principles:

* **Zero-Impact to User Experience:** The look, feel, and responsiveness of the Streamlit UI must remain unchanged from the user's perspective. All changes will be backend-focused until the final integration step.
* **Preservation of Performance:** The application's snappy performance is a key feature. All existing caching strategies and efficient, indexed database queries must be maintained or improved.
* **Incremental and Testable Changes:** The plan is broken into discrete phases and steps. Each step must be completed and verified before the next begins. This minimizes risk and allows for clear progress tracking.
* **Clarity and Maintainability:** The end goal is a clean, logical, and well-documented codebase that accurately reflects the data model and is easy for future developers to maintain.

---

## 2. Phase 1: Foundational Model Refactoring

**Objective:** To create accurate Pydantic models that correctly represent the database structure. This is the foundation upon which all other fixes will be built.

### **Step 1.1: Create Rich Asset Models**

* **Objective:** Replace the generic `Asset` model with a set of specific models that can accurately describe each asset type and its location (file-based vs. database-hosted).
* **Files to Modify:** `models.py`
* **Tasks:**
    1.  Create a `AssetType` Enum: `class AssetType(str, Enum): IMAGE="image", AUDIO="audio", VIDEO="video", PAGE="page", TABLE="table"`.
    2.  Create a base `BaseAsset` model with common fields: `uuid: str`, `name: str`, `asset_type: AssetType`.
    3.  Create a `FileAsset` model inheriting from `BaseAsset` with an added `file_path: str` field. This will be used for Images, Audio, and Videos.
    4.  Create a `ContentAsset` model inheriting from `BaseAsset` with an added `html_content: str` field. This will be used for Pages and Tables.
    5.  Create a `LinkAsset` model for external links with a `url: str` field.
* **Definition of Done (DoD):**
    * ✅ The `models.py` file contains the new `AssetType` enum and the `FileAsset`, `ContentAsset`, and `LinkAsset` Pydantic models.
    * ✅ The old, simple `Asset` model is removed.
    * ✅ The code remains runnable with no breaking changes yet.

### **Step 1.2: Redesign the `Question` Model**

* **Objective:** Update the `Question` model to use the new asset models and to logically separate different types of content.
* **Files to Modify:** `models.py`
* **Tasks:**
    1.  In the `Question` model, remove the generic `assets: list[Asset]` field.
    2.  Add new fields to hold the categorized assets:
        * `primary_question_assets: list[FileAsset] = []`
        * `primary_explanation_assets: list[FileAsset] = []`
    3.  Add new fields to hold the raw HTML that will be processed by the service layer:
        * `raw_question_html: str`
        * `raw_explanation_html: str`
    4.  Add fields for the final, processed HTML:
        * `processed_question_html: str = ""`
        * `processed_explanation_html: str = ""`
* **Definition of Done (DoD):**
    * ✅ The `Question` model in `models.py` reflects the new structure with distinct fields for primary assets and raw/processed HTML.
    * ✅ The application is temporarily broken, as the adapter and service no longer align with this model. This is expected and will be fixed in the next phase.

---

## 3. Phase 2: Data Access and Service Layer Refactoring

**Objective:** To create a single, efficient service that correctly fetches data, populates the new models, and performs all necessary processing and caching.

### **Step 2.1: Create a New, Unified `QuestionService`**

* **Objective:** Consolidate all data fetching, processing, and caching logic into a single, well-structured service. This service will replace the fragmented and incorrect `services.py` and `updated_question_service.py`.
* **Files to Modify:** Create `question_service.py`. Modify `database.py`.
* **Tasks:**
    1.  Create a new file: `question_service.py`.
    2.  Inside `database.py`, create helper functions to query each of the 5 asset collections by UUID. These functions should be efficient and targeted.
    3.  In `question_service.py`, create a `QuestionService` class.
    4.  Implement a private method `_fetch_raw_question_by_id(question_id: str) -> Question`. This method will:
        * Fetch the main question document from MongoDB.
        * Fetch all primary assets listed in the `images.question` and `images.explanation` fields by calling the new helper functions in `database.py`.
        * Populate the new `Question` model, filling in `primary_question_assets` and the `raw_..._html` fields.
        * This method should be cached using `@st.cache_data` to preserve performance.
* **Definition of Done (DoD):**
    * ✅ A `get_question_by_id` call to the new service returns a `Question` object.
    * ✅ The `primary_question_assets` and `primary_explanation_assets` lists in the returned object are correctly populated with `FileAsset` objects (differentiating between Images and Audio).
    * ✅ The `raw_question_html` and `raw_explanation_html` fields contain the unprocessed HTML from the database.
    * ✅ The `processed_..._html` fields are still empty.

### **Step 2.2: Implement HTML Parsing and Asset Hydration**

* **Objective:** Implement the core logic to parse the `[[...]]` links and "hydrate" the HTML with the correct content.
* **Files to Modify:** `question_service.py`
* **Tasks:**
    1.  In `QuestionService`, create a new public method `get_hydrated_question_by_id(question_id: str) -> Question`.
    2.  This method first calls the cached `_fetch_raw_question_by_id` from the previous step.
    3.  It then calls a new private method `_hydrate_html(html: str) -> str`.
    4.  The `_hydrate_html` method will contain the logic to:
        * Use regex to find all `[[...]]` instances.
        * For each instance, determine if the content is a URL or a UUID.
        * If it's a UUID, query the asset collections (`Videos`, `Pages`, `Tables`, `Images`) to find its type.
        * Replace the `[[...]]` placeholder with the appropriate final HTML (e.g., an `<a>` tag that opens a modal for a Page, a link to a video file, etc.).
        * Handle nested assets by allowing recursive hydration if a `Page`'s HTML also contains `[[...]]`.
    5.  The results from `_hydrate_html` are used to populate the `processed_question_html` and `processed_explanation_html` fields of the `Question` object.
* **Definition of Done (DoD):**
    * ✅ Calling `get_hydrated_question_by_id` returns a fully populated `Question` object.
    * ✅ The `processed_..._html` fields now contain HTML where `[[...]]` links have been correctly replaced with functional links or content.
    * ✅ Unit tests are written to verify the hydration logic for all asset types (Video, Page, Table, external URL).

---

## 4. Phase 3: UI Integration and Cleanup

**Objective:** To integrate the new, fully functional service into the UI and remove all obsolete code.

### **Step 3.1: Integrate New Service into the UI**

* **Objective:** Update the Streamlit front end to use the new `QuestionService` and render the fully processed data.
* **Files to Modify:** `main.py`
* **Tasks:**
    1.  In `main.py`, remove all calls to the old `updated_question_service`.
    2.  Instantiate and call the new `QuestionService.get_hydrated_question_by_id`.
    3.  Update the rendering logic:
        * Render `primary_question_assets` and `primary_explanation_assets` in their dedicated UI sections, correctly handling image vs. audio types.
        * Render `processed_question_html` and `processed_explanation_html` using `st.markdown(..., unsafe_allow_html=True)`.
* **Definition of Done (DoD):**
    * ✅ The application is fully functional.
    * ✅ All asset types (Images, Audio, Videos, Pages, Tables, external links) are correctly displayed and interactive in the UI.
    * ✅ The user experience and performance are identical to or better than the original implementation.

### **Step 3.2: Code Cleanup**

* **Objective:** Remove all dead and obsolete code to finalize the refactoring.
* **Files to Modify:** Delete old files.
* **Tasks:**
    1.  Delete the file `services.py`.
    2.  Delete the file `updated_question_service.py`.
    3.  Delete the file `updated_legacy_adapter.py`.
* **Definition of Done (DoD):**
    * ✅ The obsolete files are removed from the project.
    * ✅ The application remains fully functional after their removal.
    * ✅ The project structure is clean and logical.