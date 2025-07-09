import streamlit as st
from services import QuestionService
from database import db_client
import config

# --- Initial Page Config ---
st.set_page_config(
    page_title="DocuMedica Question Bank",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Services ---
question_service = QuestionService()


# --- Helper Functions ---
@st.cache_data  # Cache the data so we don't query on every rerun
def get_filter_options():
    """Fetches unique sources and tags from the database for filter population."""
    print("Fetching filter options from DB...")
    sources = [
        s["name"] for s in db_client.find_documents(config.SOURCES_COLLECTION, {})
    ]
    pipeline = [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
    tags = [
        t["_id"]
        for t in db_client.get_collection(config.QUESTIONS_COLLECTION).aggregate(
            pipeline
        )
    ]
    return sorted(sources), sorted(tags)


# --- Session State Initialization ---
if "selected_question_id" not in st.session_state:
    st.session_state.selected_question_id = None  # Tracks the currently viewed question

# --- Sidebar for Filters ---
with st.sidebar:
    st.title("🔍 Search & Filters")
    all_sources, all_tags = get_filter_options()

    search_query = st.text_input("Search by text in question")
    selected_sources = st.multiselect("Filter by Source", options=all_sources)
    selected_tags = st.multiselect("Filter by Tags", options=all_tags)
    st.markdown("---")
    show_favorites_only = st.checkbox("Show Favorites Only ⭐")
    show_marked_only = st.checkbox("Show Marked Only 🚩")

    with st.expander("ℹ️ About & Help"):
        st.info(
            """
            This application is a local question bank viewer.

            **How to use:**
            - Use the filters on the left to search for questions.
            - Click "View Details" to see a question and its media.
            - You can favorite, mark, or add notes to any question in the detail view.
        """
        )

# --- Main Content Area ---
st.title("🩺 DocuMedica Question Bank")


def display_question_list():
    """Builds a query from filters and displays a list of matching questions."""
    query = {}
    if search_query:
        query["text"] = {"$regex": search_query, "$options": "i"}
    if selected_sources:
        query["source"] = {"$in": selected_sources}
    if selected_tags:
        query["tags"] = {"$in": selected_tags}
    if show_favorites_only:
        query["is_favorite"] = True
    if show_marked_only:
        query["is_marked"] = True

    # Define the fields to retrieve (projection). 1 means include, 0 means exclude.
    projection = {
        "question_id": 1,
        "is_favorite": 1,
        "is_marked": 1,
        "source": 1,
        "tags": 1,
        "_id": 1,  # We need _id for the button key
    }
    filtered_questions = db_client.find_documents(
        config.QUESTIONS_COLLECTION, query, projection=projection
    )
    st.subheader(f"Found {len(filtered_questions)} Questions")

    if not filtered_questions:
        st.info("No questions match the current filters. Try adjusting your search.")
        return

    for q in filtered_questions:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                fav_icon = "⭐" if q.get("is_favorite") else ""
                mark_icon = "🚩" if q.get("is_marked") else ""
                st.markdown(f"**{q['question_id']}** {fav_icon} {mark_icon}")
                st.caption(
                    f"Source: {q['source']} | Tags: {', '.join(q.get('tags', []))}"
                )
            with col2:
                if st.button("View Details", key=q["_id"]):
                    st.session_state.selected_question_id = q["question_id"]
                    st.rerun()
            st.markdown("---")


def display_question_detail():
    """Displays a single, fully rendered question with interactive management controls."""
    q_id = st.session_state.selected_question_id
    question = question_service.get_question_by_id(q_id)

    if not question:
        st.error("Question not found!")
        st.session_state.selected_question_id = None
        return

    # --- Action Buttons ---
    col1, col2, col3, col_spacer = st.columns([2, 2, 2, 6])
    if col1.button("⬅️ Back to List"):
        st.session_state.selected_question_id = None
        st.rerun()

    fav_text = "Unfavorite ⭐" if question.is_favorite else "Favorite ⭐"
    if col2.button(fav_text):
        question_service.toggle_favorite(q_id)
        st.rerun()

    mark_text = "Unmark 🚩" if question.is_marked else "Mark 🚩"
    if col3.button(mark_text):
        question_service.toggle_marked(q_id)
        st.rerun()

    st.markdown("---")

    # --- Display Rendered Question ---
    st.subheader(f"Viewing: {question.question_id}")
    st.markdown(question_service.render_question_html(question), unsafe_allow_html=True)

    st.markdown("---")

    # --- Notes Section ---
    st.subheader("Your Notes")
    current_notes = question.notes or ""
    notes_input = st.text_area(
        "Add or edit your notes here:",
        value=current_notes,
        height=150,
        label_visibility="collapsed",
    )
    if st.button("Save Notes"):
        question_service.update_notes(q_id, notes_input)
        st.success("Notes saved!")
        st.rerun()


# --- Main Application Router ---
if st.session_state.selected_question_id is None:
    display_question_list()
else:
    display_question_detail()
