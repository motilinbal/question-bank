# Master Reference: test_db Database Architecture

**Version:** 2.0
**Date:** July 11, 2025
**Author:** Gemini Engineering Intelligence

---

## 1. Overview and Core Architectural Issue

This document provides a definitive guide to the structure of the `test_db` MongoDB database. A thorough investigation has revealed that the database's architecture is complex and defined by a critical inconsistency: **two different and co-existing systems are used to link questions to their multimedia assets.**

This duality is the primary source of complexity when interacting with the database. Any application built on this database must be specifically coded to handle both systems to avoid missing content and functionality.

The two systems are:
1.  **The Structured `images` Field**: A dedicated field in the `Questions` collection for listing primary, non-inline assets like key images and audio clips.
2.  **The Unstructured `[[...]]` Embedded Link**: A special double-bracket syntax used directly within HTML content to link to inline, contextual assets like videos, interactive pages, tables, and external websites.

---

## 2. The `Questions` Collection

The `Questions` collection is the central hub of the database. Each document represents a single question with its associated text, choices, and links to assets.

| Field | Type | Description |
| :--- | :--- | :--- |
| `_id` | `String` (UUID) | The unique identifier for the question document. |
| `name` | `String` | An internal name or identifier for the question, which can sometimes be an ID from the source system. |
| `source` | `String` | The origin of the content (e.g., `lecturio2`, `uworld3`, `archer1`, `sketchy`). |
| `tags` | `Array` of `String` | A list of tags classifying the question by subject (e.g., `Pediatrics`, `Cardiovascular System`). |
| `images` | `Object` | **System 1 Linking.** An object containing arrays of asset UUIDs. This field is misleadingly named as it also contains IDs for Audio assets. It is used for primary, non-inline media. |
| `images.question`| `Array` of `String` | An array of UUIDs for primary assets associated with the question body. |
| `images.explanation`| `Array` of `String` | An array of UUIDs for primary assets associated with the explanation. |
| `question` | `String` (HTML) | The HTML content of the question itself. May contain `[[...]]` links. |
| `choices` | `Array` of `Object`| An array representing the multiple-choice options. |
| `choices[n].text`| `String` (HTML) | The HTML content for the choice. |
| `choices[n].id`| `Number` | The identifier for the choice. |
| `choices[n].is_correct`| `Boolean` | Indicates if this choice is the correct answer. |
| `explanation` | `String` (HTML) | The HTML content for the question's explanation. May contain `[[...]]` links. |
| `text` | `String` | A plain text representation of the entire question, choices, and explanation, likely for search indexing. |
| `difficult` | `Boolean` | A flag indicating if the question is considered difficult. |
| `flagged` | `Boolean` | A flag for internal review or user-reported issues. |
| `group`| `Array` | Purpose not definitively determined, but appears to be empty in most cases. |

---

## 3. The Asset Collections: File-Based vs. Database-Hosted

Assets are stored across five different collections, which fall into two distinct categories based on where their content resides.

### 3.1. File-Based Media Assets (`Images`, `Audio`, `Videos`)

These collections store metadata about media files. The actual content is a physical file on the server's filesystem, not in the database.

* **`Images` Collection**: Stores image files.
* **`Audio` Collection**: Stores audio files.
* **`Videos` Collection**: Stores video files.

| Field | Type | Description |
| :--- | :--- | :--- |
| `_id` | `String` (UUID) | Unique identifier for the asset. |
| `name` | `String` | **Crucial Field.** The filename of the asset (e.g., `anatomy.jpg`, `heartbeat.mp3`). The application must use this name to construct the full file path by joining it with the appropriate directory path defined in `config.py` (e.g., `IMAGES_DIR`, `AUDIO_DIR`). |
| `original_name`| `String` | The original filename from the source system. |
| `source` | `String` | The origin of the content. |
| `meta` | `String` | Metadata field, typically empty. |
| `codes` | `Array` | An array of numeric codes from the source system. |

### 3.2. Database-Hosted Content Assets (`Pages`, `Tables`)

These collections store their full content directly within the database document itself as an HTML string. They are self-contained and do not point to external files.

* **`Pages` Collection**: Stores complex, self-contained HTML documents for interactive content.
* **`Tables` Collection**: Stores pre-formatted HTML tables.

| Field | Type | Description |
| :--- | :--- | :--- |
| `_id` | `String` (UUID) | Unique identifier for the asset. This is the ID used in `[[...]]` links. |
| `html` | `String` (HTML) | **Crucial Field.** The full HTML content of the asset. **This HTML can itself contain `[[...]]` links to other assets**, creating nested dependencies that the application must be able to resolve recursively. |
| `source` | `String` | The origin of the content. (Not present in all `Pages` documents). |
| `...` | | Other fields like `link_id`, `css`, `js`, `text`, `codes` may be present. |

---

## 4. Asset Processing Logic: A Developer's Guide

To correctly render a question and all its media, the application **must** implement a two-part processing flow.

### **Part 1: Process Primary, File-Based Assets via `images` Field**

This logic handles the assets that are intended to be displayed in a primary, non-inline context.

1.  After fetching a question document, check the `images.question` and `images.explanation` arrays.
2.  For each UUID found, query the `Images` and `Audio` collections to find the corresponding asset document.
3.  From the asset document, extract the filename from the `name` field.
4.  Construct the full, server-relative path to the asset file using the directory paths specified in `config.py` (e.g., `assets/images/anatomy.jpg`).
5.  Render these assets in a dedicated section of the UI, such as a gallery below the question text.

### **Part 2: Process Inline Content via `[[...]]` Links**

This logic handles the replacement of inline placeholders within the HTML content.

1.  Take the raw HTML from the `question` and `explanation` fields.
2.  Use a regular expression (e.g., `/\[\[(.*?)\]\]/g`) to find all occurrences of the `[[...]]` pattern.
3.  For each match, extract the content within the brackets and determine its type:
    * **If it's an external URL** (starts with `http`): Replace the `[[...]]` placeholder with a standard external hyperlink (`<a href="..." target="_blank">...</a>`).
    * **If it's a UUID**: This is an internal asset. You must determine its type:
        1.  **Query the `Pages` and `Tables` collections first.** If a match is found, the asset is database-hosted. Replace the `[[...]]` placeholder with a link that, when clicked, fetches the `html` content from that asset document and displays it (e.g., in a modal). Be aware that this fetched HTML may require its own `[[...]]` parsing (recursion).
        2.  **If not found, query `Images`, `Videos`, and `Audio`.** If a match is found, the asset is file-based. Extract the `name` field, construct the file path as described in Part 1, and replace the `[[...]]` placeholder with a link that opens or plays the media file.

By implementing this comprehensive, two-part logic, an application can accurately interpret the database's complex structure and correctly display all intended content.