# Technical Memo: A Deep-Dive into the DocuMedica Application Refactoring

**Date:** July 11, 2025
**Status:** In Progress
**Author:** Gemini Engineering Intelligence

## 1. Background and Initial Objective

This document details the comprehensive debugging and refactoring process undertaken for the DocuMedica Question Bank application. The initial goal was to debug a legacy codebase to correctly display multimedia assets (images, audio, video) stored in a MongoDB database.

Early investigation revealed that the application's failure was not a simple bug but was rooted in a profound misunderstanding of the database's architecture. The codebase was built on incorrect assumptions, leading to a complete failure to retrieve and display most asset types.

This discovery shifted the project's objective from simple debugging to a full-scale refactoring of the application's data access and service layers to align them with the true, complex structure of the data.

---

## 2. The Refactoring Journey: Problems Solved

Our process was methodical, following a "detective" mindset to first understand the problem completely before attempting a solution.

### 2.1. Discovery: The "Two Systems" Problem

Our initial database exploration uncovered the core architectural flaw: two distinct and competing systems were used to link questions to assets.

* **System 1: The Structured `images` Field:** An explicit list of UUIDs for primary, non-inline assets (Images and Audio).
* **System 2: The Unstructured `[[...]]` Links:** `<a>` tags embedded directly in the HTML, where the `href` attribute contained a `[[UUID]]` placeholder. This system was used for all asset types, including Videos, Pages, and Tables.

**Action Taken:** We created a master reference document detailing this dual-system architecture. This became our "ground truth" for the refactoring effort.

### 2.2. Solution: A Unified Service Layer

We abandoned the old, fragmented services and adapters, which were based on false assumptions.

* **Action Taken:** We created a new, unified `question_service.py` and rich Pydantic `models.py`.
* **Outcome:** This new service was designed from the ground up to understand both linking systems. It correctly fetches primary assets from the `images` field and contains a hydration method (`_hydrate_html`) to process the embedded `[[...]]` links.

### 2.3. The Battle for HTML Hydration

The most complex part of the refactoring was teaching the `_hydrate_html` function to correctly replace the placeholder `<a>` tags.

* **Problem 1: Nested Tags.** Our first attempt resulted in corrupted, nested `<a>` tags because our regex was too specific and only replaced the `[[...]]` part, not the entire tag.
* **Problem 2: Newlines.** Our second attempt failed because the raw HTML in the database contained newline characters (`\n`) that broke our regex match.
* **Action Taken:** We used a systematic debugging process:
    1.  We created a test script (`debug_service.py`) to isolate the service from the UI.
    2.  We printed the `repr()` of the raw HTML string from the database to discover the hidden newline characters.
    3.  We crafted a final, precise regex (`<a[^>]*href="\[\[(.*?)\]\]"[^>]*>(.*?)</a>`) and used the `re.DOTALL` flag to ensure it correctly matched the multiline pattern.
* **Outcome:** We achieved a perfect HTML transformation, where the service correctly generates clean `<a>` tags with the proper URLs and preserves the original link text.

### 2.4. Restoring the User Interface

Our initial attempts to integrate the new service broke the UI, specifically the interactive choice selection.

* **Action Taken:** We took a step back and surgically re-integrated the original, working code for the choice UI from a previous version.
* **Outcome:** The interactive choice selection (radio buttons, submit button, red/green feedback) was fully restored, providing a stable foundation for tackling the final bugs.

---

## 3. Current Status: The Final Open Issues

After successfully refactoring the backend and stabilizing the core UI, we are left with two specific, reproducible frontend bugs.

* **Bug #1: Asset Loading Failure.**
    * **Symptom:** Clicking a hyperlink for any internally hosted asset (e.g., an image, table, or video) opens a blank browser tab.
    * **Evidence:** The browser's developer console shows a "disallowed MIME type" error. For example, when requesting an image, the browser receives a file with a `text/html` MIME type instead of the expected `image/jpeg`. This proves the Streamlit server is intercepting the request and sending the main application's index.html file instead of the asset.
    * **Status:** This is a critical functional bug.

* **Bug #2: Broken UI Reactivity.**
    * **Symptom:** The `+` and `-` buttons for changing the text size do not produce a visual update on the screen.
    * **Evidence:** We have proven that a simple `st.button` with `st.rerun()` *does* work on the page. However, the font size buttons specifically fail.
    * **Status:** This is a high-priority user experience bug.

---

## 4. In-Depth Analysis of Open Issues

This analysis moves beyond symptoms to address the root cause, based on our detective work.

### 4.1. Analysis of the Asset Loading Failure

The key piece of evidence is that `st.image("assets/images/file.jpg")` works correctly, but `<a href="assets/images/file.jpg">` does not.

This proves that the problem is **not file permissions or incorrect paths**. The Python script can access the files. The problem is a fundamental limitation of Streamlit's development server.

* **The Root Cause: Route Hijacking.** Streamlit's server is designed to be a single-page application (SPA) runner. By default, it does not act as a general-purpose file server. When your browser makes an HTTP request to `http://localhost:8501/assets/images/file.jpg`, the Streamlit server does not know it's supposed to look for a file. Instead, it assumes this is a route for the main application and serves the default `index.html` page. The browser receives this HTML, sees that its MIME type (`text/html`) does not match what it expected for an image, and blocks it for security reasons.
* **Why `st.image()` Works:** The `st.image()` component works differently. It reads the image file into memory on the **backend** (in Python), encodes it (often as Base64), and sends that data to the frontend as part of the main application's data stream. It does not rely on the browser making a separate HTTP request to a URL.

**Conclusion:** We cannot use simple `<a>` tags with relative paths to serve local files. This approach is architecturally incompatible with how the Streamlit server operates.

### 4.2. Analysis of the UI Reactivity Failure

The key piece of evidence here is that a simple `st.button` test works, but the font buttons in their original layout do not.

* **The Root Cause: Layout Component Interference.** Our test proved that the basic `st.rerun()` functionality is not broken. However, the original layout placed the font buttons inside a deeply nested structure: `st.columns` inside another `st.columns`. In complex UI libraries like Streamlit, deeply nested components can sometimes create isolated "scopes" that can interfere with or "swallow" the signals that trigger a page-wide rerender. When we removed the columns, the buttons worked perfectly.

**Conclusion:** The UI reactivity bug is a direct result of the complex `st.columns` layout we were using. The solution is to use a simpler, more stable layout for these buttons.

---

## 5. Strategic Recommendations for Next Steps

Based on this analysis, the path forward is clear. We must work *with* the Streamlit framework, not against it.

1.  **Solve Asset Loading First:** This is the most critical bug.
    * **The Strategy:** Abandon the use of `<a>` tags for local file assets. We must use Streamlit's native components.
    * **The Plan:** We need a way to replace the `<a>` tag placeholders in our HTML with something that can trigger a Streamlit component on the frontend. The best user experience would be to display the asset in a modal dialog or an expander directly on the page, rather than opening a new tab. This will require a creative solution that combines session state and conditional rendering.

2.  **Solve UI Reactivity Second:**
    * **The Strategy:** Re-implement the button layout using a simpler, more robust method.
    * **The Plan:** A single `st.columns` call that aligns the buttons to the right is a standard and stable pattern that should not interfere with the render loop.

This concludes the debrief. We have a clear understanding of the final two challenges and a robust, evidence-based strategy for solving them.