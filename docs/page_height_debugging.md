## **DocuMedica Page Rendering: A Debugging & Architectural Analysis Report**

**Date:** July 13, 2025
**Status:** Concluded with a stable, albeit compromised, solution.

### **1. Executive Summary**

This document provides a definitive record of the debugging process undertaken to resolve a critical display bug in the DocuMedica application. The initial problem was that embedded `Page` assets, which are self-contained HTML documents with background images, were being truncated, preventing users from viewing their full content.

The investigation evolved through several phases, methodically eliminating potential causes and uncovering deep architectural principles of the Streamlit framework. We successfully fixed numerous underlying issues, including inefficient data handling and incorrect file pathing. The root cause was ultimately identified as a fundamental limitation in Streamlit's standard components, which do not support dynamic iframe resizing based on content.

The application is now in a **stable state**. The inefficient workarounds have been removed, and the code now uses Streamlit's official static file serving mechanism. However, to maintain stability and avoid introducing significant complexity, a compromise was made: `Page` assets are now displayed in a fixed-height container with a scrollbar.

This document details the evidence, the failures, the lessons learned, and the rationale behind the application's current architecture.

-----

### **2. The Debugging Journey: From Symptom to Root Cause**

Our investigation followed a rigorous, evidence-based path. Each hypothesis was tested, and the results informed the next step.

#### **Phase 1: Initial Hypothesis - Flawed Height Calculation**

  * **Initial Belief:** We first assumed the logic for calculating the `Page` height, which was based on the background image's dimensions, was simply implemented incorrectly.
  * **Testing & Evidence:** We hardcoded the display height to a large value (`800px`). The truncation *persisted*.
  * **Conclusion:** This test proved that our server-side height calculation was not the primary cause of the bug. The problem lay deeper in the rendering process.

#### **Phase 2: Uncovering the Base64 Workaround**

  * **Hypothesis:** There was a discrepancy between how the server measured the image and how the browser rendered it.
  * **Testing & Evidence:** We inspected the rendered HTML in the browser's developer tools. We discovered that the `<img>` tag's `src` attribute was not a file path but an enormous **Base64-encoded data string**.
  * **Conclusion:** This was a critical breakthrough. The application was not linking to images but embedding them directly into the HTML. This was identified as a major performance issue and the likely cause of the browser struggling to calculate the layout, leading to truncation.

#### **Phase 3: The Architecturally Correct Refactor**

  * **Hypothesis:** The Base64 workaround was implemented to overcome Streamlit's default inability to serve static files from standard HTML tags. The correct solution was to replace this workaround with Streamlit's official static file serving feature.
  * **Testing & Evidence:** We implemented the documented solution:
    1.  Created `.streamlit/config.toml` with `enableStaticServing = true`.
    2.  Renamed the `assets` directory to `static`.
    3.  Removed all Base64 logic from `question_service.py`.
    4.  Modified the code to generate the mandatory `/app/static/` URL paths.
  * **Result:** This was a partial success. The inefficient Base64 workaround was eliminated, and the browser correctly requested the image from the static path. However, the truncation issue returned in a new form: the `iframe` now defaulted to a very small height (`150px`).

#### **Phase 4: The Final Hurdle - Dynamic Iframe Sizing**

  * **Hypothesis:** With all data-loading issues solved, the final problem was that the `st.html` component does not automatically resize to fit its content. We attempted to solve this with a JavaScript-based communication channel using `window.parent.postMessage`.
  * **Testing & Evidence:** We implemented a diagnostic test to verify the communication channel. A script inside the `iframe` logged a message and attempted to `postMessage` its height. The console output definitively showed that the script **was running** but the parent page **was not receiving the message**.
  * **Conclusion:** This was the final, crucial piece of evidence. [cite\_start]The sandboxing architecture of the `st.html` component actively blocks this form of communication. [cite: 7]

-----

### **3. Key Architectural Lessons Learned**

This process provided deep insights into the Streamlit framework's design philosophy.

  * **Streamlit Components are Sandboxed:** All content rendered via `st.components.v1.html` is placed in an isolated `iframe`. [cite\_start]This is a deliberate security and stability feature to prevent custom code from breaking the main application. [cite: 1, 3] The consequence is that there is no simple, direct way for the parent app to know the size of the content within the `iframe`.
  * **`postMessage` is Blocked:** The standard web technique for `iframe` communication is intentionally blocked for the basic `st.html` component. [cite\_start]The only sanctioned method for bi-directional communication is to build a full **custom component**. [cite: 2]
  * [cite\_start]**The "Correct" Solution is Complex:** The definitive, architecturally sound solution involves creating a bespoke bi-directional component that uses a library like `iframe-resizer.js` and leverages the official `Streamlit.setFrameHeight()` JavaScript function. [cite: 10, 16] This pattern, proven by popular community components, provides perfect auto-resizing but adds significant complexity to the project (requiring a separate frontend build process with Node.js and TypeScript).

-----

### **4. Current State of the Application and Rationale**

Given the complexity of the "correct" architectural solution, a pragmatic engineering decision was made to pause development and implement a stable compromise.

#### **Current Implementation:**

1.  **Static File Serving:** The application correctly uses Streamlit's native static file server. All assets are in the `/static` directory, and all paths are correctly generated.
2.  **No Base64 Encoding:** The inefficient and buggy Base64 workaround has been permanently removed from the codebase.
3.  **Fixed-Height Iframe:** `Page` assets are now rendered in `main.py` using a hardcoded, but generous, height with scrolling enabled:
    ```python
    # From main.py, inside the diagnostic test
    test_height = 1200
    components.html(asset.html_content, height=test_height, scrolling=True)
    ```
4.  **No Dynamic Resizing:** There is no JavaScript communication attempting to resize the `iframe`.

#### **Rationale for this Compromise:**

  * **Stability:** This solution is stable and predictable. It removes all the complex, non-working code and relies only on the standard, documented behavior of the `st.html` component.
  * **Functionality:** The user can view the **entire** content of the `Page` asset without truncation by using the vertical scrollbar. While not ideal, this fully resolves the original bug.
  * **Reduced Complexity:** It avoids the need to add a separate frontend build system (Node.js, npm, TypeScript) to the project, keeping the pure-Python architecture intact for now.

This state represents a considered trade-off between the perfect user experience and the current project's complexity constraints. The groundwork has been laid to implement the full custom component solution in the future, should the business needs justify the additional development investment.