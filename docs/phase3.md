# DocuMedica Refactoring: Phase 3 Implementation Plan

## **Objective: User Interface Development with Streamlit**

The goal of Phase 3 is to build a fully functional, interactive user interface for the DocuMedica application using the **Streamlit** library. This phase will leverage all the backend services created in Phase 2 to provide users with the ability to search, filter, view, and manage questions in a simple and intuitive web-based GUI.

**Estimated Time to Complete:** 6-8 hours

---

### **Task 3.1: Basic App Layout and State Management**

* **Goal**: Create the main application file (`main.py`) and establish the fundamental UI structure, including a sidebar for controls and a main area for content. We will also initialize Streamlit's session state to manage user interactions.

* **Steps**:

    1.  **Restructure `main.py`**: The `main.py` file will now become the entry point for the Streamlit application. The previous test code can be removed or commented out.
    2.  **Initialize Streamlit and Services**: Import necessary libraries and instantiate the services.
    3.  **Set Up `st.session_state`**: Initialize variables in the session state. This is crucial for remembering the current state across user interactions (e.g., which question is selected).
    4.  **Create Sidebar and Main Area**: Use `st.sidebar` to define the navigation and filter panel and `st.container` for the main content.

* **Code Implementation (`main.py`)**:

    ```python
    # main.py
    import streamlit as st
    from services import QuestionService
    from database import db_client # To get all sources/tags for filters
    import os
    import config

    # --- Initial Page Config ---
    st.set_page_config(
        page_title="DocuMedica Question Bank",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Initialize Services ---
    question_service = QuestionService()

    # --- Session State Initialization ---
    if "selected_question_id" not in st.session_state:
        st.session_state.selected_question_id = None # Tracks the currently viewed question

    # --- UI Layout ---
    st.title("🩺 DocuMedica Question Bank")
    st.sidebar.title("Search & Filters")

    # This function will hold the logic for displaying the list of questions
    def display_question_list():
        st.write("List of questions will appear here.")

    # This function will display the detailed view of a single question
    def display_question_detail():
        st.write(f"Detailed view for question: {st.session_state.selected_question_id}")
        # Add a back button
        if st.button("⬅️ Back to List"):
            st.session_state.selected_question_id = None
            st.experimental_rerun() # Rerun the script to update the view

    # --- Main App Logic (Router) ---
    if st.session_state.selected_question_id is None:
        display_question_list()
    else:
        display_question_detail()

    # --- Ensure DB connection is closed on exit ---
    # (Streamlit apps run top-to-bottom on each interaction, so we don't explicitly close here.
    # The singleton pattern in `database.py` handles the connection.)
    ```

* **Definition of Done (DoD)**:
    * ✅ Running `streamlit run main.py` successfully launches the web application.
    * ✅ The app displays the main title "DocuMedica Question Bank".
    * ✅ A sidebar is visible with the title "Search & Filters".
    * ✅ The main content area initially shows the placeholder "List of questions will appear here."
    * ✅ `st.session_state` is properly initialized.

---

### **Task 3.2: Search and Filtering UI**

* **Goal**: Populate the sidebar with interactive widgets that allow users to filter questions based on various criteria.

* **Steps**:

    1.  **Fetch Filter Data**: Query the database once to get all unique sources and tags to populate the filter options.
    2.  **Add Widgets to Sidebar**: Implement `st.text_input` for text search, `st.multiselect` for sources and tags, and `st.checkbox` for boolean flags.
    3.  **Store Filter Values**: Store the selected filter values in variables.

* **Code Implementation (within `main.py`)**:

    ```python
    # Add this helper function at the top of main.py
    @st.cache_data # Cache the data so we don't query on every rerun
    def get_filter_options():
        print("Fetching filter options from DB...")
        sources = [s['name'] for s in db_client.find_documents("sources", {})]
        # Use aggregation to get all unique tags from the questions collection
        pipeline = [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
        tags = [t['_id'] for t in db_client.get_collection("questions").aggregate(pipeline)]
        return sources, tags

    # Inside main.py, replace the st.sidebar.title line with this block:
    with st.sidebar:
        st.title("🔍 Search & Filters")

        # Fetch options for filters
        all_sources, all_tags = get_filter_options()

        # --- Filter Widgets ---
        search_query = st.text_input("Search by text in question")
        selected_sources = st.multiselect("Filter by Source", options=all_sources)
        selected_tags = st.multiselect("Filter by Tags", options=all_tags)

        st.markdown("---") # Visual separator

        show_favorites_only = st.checkbox("Show Favorites Only ⭐")
        show_marked_only = st.checkbox("Show Marked Only 🚩")
    ```

* **Definition of Done (DoD)**:
    * ✅ The sidebar now contains a text input, two multiselect boxes, and two checkboxes.
    * ✅ The "Source" and "Tags" multiselect boxes are correctly populated with data from the MongoDB database.
    * ✅ The app uses `@st.cache_data` to avoid re-querying the database on every user interaction.

---

### **Task 3.3: Displaying the Filtered Question List**

* **Goal**: Implement the logic to query the database using the selected filters and display the results as a clickable list in the main content area.

* **Steps**:

    1.  **Build a MongoDB Query**: Dynamically construct a query dictionary based on the values from the sidebar widgets.
    2.  **Fetch Questions**: Use `db_client.find_documents` to get the list of matching questions.
    3.  **Display Results**: Iterate through the results and display each question's ID and a text snippet. Use `st.button` for each item to make it selectable.

* **Code Implementation (replace the `display_question_list` function in `main.py`)**:

    ```python
    def display_question_list():
        # --- Build DB Query from Filters ---
        query = {}
        if search_query:
            query["text"] = {"$regex": search_query, "$options": "i"} # Case-insensitive search
        if selected_sources:
            query["source"] = {"$in": selected_sources}
        if selected_tags:
            query["tags"] = {"$in": selected_tags}
        if show_favorites_only:
            query["is_favorite"] = True
        if show_marked_only:
            query["is_marked"] = True

        # --- Fetch and Display Questions ---
        filtered_questions = db_client.find_documents("questions", query)

        st.subheader(f"Found {len(filtered_questions)} Questions")

        if not filtered_questions:
            st.info("No questions match the current filters. Try adjusting your search.")
            return

        for q in filtered_questions:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    fav_icon = "⭐" if q.get('is_favorite') else ""
                    mark_icon = "🚩" if q.get('is_marked') else ""
                    st.markdown(f"**{q['question_id']}** {fav_icon} {mark_icon}")
                    st.caption(f"Source: {q['source']} | Tags: {', '.join(q.get('tags', []))}")
                with col2:
                    if st.button("View Details", key=q['_id']):
                        st.session_state.selected_question_id = q['question_id']
                        st.experimental_rerun()
                st.markdown("---")
    ```

* **Definition of Done (DoD)**:
    * ✅ The main area displays a list of questions that updates in real-time as filters are changed in the sidebar.
    * ✅ The count of found questions is displayed correctly.
    * ✅ Each question in the list shows its ID, favorite/marked status, source, and tags.
    * ✅ Clicking the "View Details" button for a question correctly updates `st.session_state.selected_question_id` and switches the view.

---

### **Task 3.4: Detailed Question View and Interactive Controls**

* **Goal**: Implement the detailed view that shows the fully rendered question. Add interactive buttons to this view to allow users to favorite, mark, and add notes to the question.

* **Steps**:

    1.  **Fetch Full Question Data**: Use the `question_service` to get the `Question` model instance.
    2.  **Render HTML**: Use `question_service.render_question_html` to get the full HTML, including media. Use `st.markdown(..., unsafe_allow_html=True)` to display it.
    3.  **Add Action Buttons**: Create buttons for "Toggle Favorite," "Toggle Marked," and a `st.text_area` for notes.
    4.  **Connect Buttons to Services**: Wire the `on_click` events of the buttons to the corresponding methods in the `QuestionService`.

* **Code Implementation (replace `display_question_detail` function in `main.py`)**:

    ```python
    def display_question_detail():
        q_id = st.session_state.selected_question_id
        question = question_service.get_question_by_id(q_id)

        if not question:
            st.error("Question not found!")
            st.session_state.selected_question_id = None
            return

        # --- Action Buttons ---
        col1, col2, col3, col4 = st.columns([2, 2, 2, 6])
        with col1:
            if st.button("⬅️ Back to List"):
                st.session_state.selected_question_id = None
                st.experimental_rerun()
        with col2:
            fav_text = "Unfavorite ⭐" if question.is_favorite else "Favorite ⭐"
            if st.button(fav_text):
                question_service.toggle_favorite(q_id)
                st.experimental_rerun()
        with col3:
            mark_text = "Unmark 🚩" if question.is_marked else "Mark 🚩"
            if st.button(mark_text):
                question_service.toggle_marked(q_id)
                st.experimental_rerun()

        st.markdown("---")

        # --- Display Rendered Question ---
        st.subheader(f"Viewing: {question.question_id}")
        rendered_html = question_service.render_question_html(question)
        # To serve local files, we need to make paths accessible
        # For simplicity in this local app, we assume Streamlit runs from the root.
        # A more robust solution might involve base64 encoding images.
        rendered_html = rendered_html.replace("src='", f"src='{config.ASSETS_DIR}/")
        st.markdown(rendered_html, unsafe_allow_html=True)

        st.markdown("---")

        # --- Notes Section ---
        st.subheader("Your Notes")
        current_notes = question.notes or ""
        notes_input = st.text_area("Add or edit your notes here:", value=current_notes, height=150)
        if st.button("Save Notes"):
            question_service.update_notes(q_id, notes_input)
            st.success("Notes saved!")
            st.experimental_rerun()
    ```

* **Definition of Done (DoD)**:
    * ✅ The detailed view correctly displays the fully rendered question, including embedded images, pages, etc.
    * ✅ Clicking the "Back to List" button returns the user to the question list view.
    * ✅ Clicking the favorite/mark buttons correctly calls the service and updates the button's text on the next run.
    * ✅ The notes `text_area` is pre-populated with existing notes.
    * ✅ Clicking "Save Notes" successfully updates the notes in the database and provides user feedback.

---

**Phase 3 Completion Review**: With all tasks completed, the DocuMedica application is now a fully-featured, standalone application. Users can interact with the data through a clean web interface, realizing the project's core vision. The final step would be packaging and testing.