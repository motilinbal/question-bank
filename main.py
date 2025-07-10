import streamlit as st
from database import db_client
import config
from updated_legacy_adapter import updated_legacy_adapter
from updated_question_service import updated_question_service
from bs4 import BeautifulSoup
import re

# --- Initial Page Config ---
st.set_page_config(
    page_title="DocuMedica Question Bank",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialize Services ---
question_service = updated_question_service

# --- Question Function (removed caching to fix bug where all questions showed same content) ---
def get_cached_question(question_id):
    """Fetch question data - caching removed to prevent showing wrong questions"""
    return question_service.get_question_by_id(question_id)

def clean_html_content(html_string):
    """Clean HTML content to remove artifacts and malformed tags"""
    if not html_string:
        return ""
    
    # Remove the specific artifacts mentioned - handle various patterns
    cleaned = html_string
    
    # Remove </div></div> as single string
    cleaned = cleaned.replace("</div></div>", "")
    
    # Remove line-separated </div> artifacts with various whitespace patterns
    cleaned = re.sub(r'</div>\s*\n\s*</div>', '', cleaned)
    cleaned = re.sub(r'</div>\s*</div>', '', cleaned)
    
    # Remove trailing orphaned </div> tags
    cleaned = re.sub(r'</div>\s*$', '', cleaned.strip())
    
    # Remove multiple consecutive </div> tags
    cleaned = re.sub(r'(</div>\s*){2,}', '', cleaned)
    
    # Remove <p> tags using regex for thorough cleaning
    cleaned = re.sub(r'</?p[^>]*>', '', cleaned)
    
    # Clean up extra whitespace that might be left behind
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


# --- Helper Functions ---
@st.cache_data  # Cache the data so we don't query on every rerun
def get_filter_options():
    """Fetches unique sources and tags from the database for filter population."""
    print("Fetching filter options from DB...")
    
    # Check if database connection is available
    if db_client.db is None:
        st.error("❌ Database connection failed. Please check your MongoDB connection.")
        return [], []
    
    try:
        # Use updated legacy adapter to get sources and tags
        sources = updated_legacy_adapter.get_sources()
        tags = updated_legacy_adapter.get_tags()
        return sources, tags
    except Exception as e:
        st.error(f"❌ Error fetching filter options: {e}")
        return [], []


# --- Session State Initialization ---
if "selected_question_id" not in st.session_state:
    st.session_state.selected_question_id = None  # Tracks the currently viewed question
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "question_list" not in st.session_state:
    st.session_state.question_list = []
if "last_query" not in st.session_state:
    st.session_state.last_query = {}
if "page_size" not in st.session_state:
    st.session_state.page_size = 20

# --- New Session State for Interactive Question Experience ---
if "font_size" not in st.session_state:
    st.session_state.font_size = 18  # Default font size in pixels
if "selected_answer" not in st.session_state:
    st.session_state.selected_answer = None  # Tracks which choice the user selects
if "submitted" not in st.session_state:
    st.session_state.submitted = False  # Tracks if the user has submitted their answer
if "show_explanation" not in st.session_state:
    st.session_state.show_explanation = False  # Controls explanation visibility

# --- Question Caching for Performance ---
if "current_question" not in st.session_state:
    st.session_state.current_question = None  # Will hold the full question object
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = None  # Tracks the ID of the question being displayed

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

    # --- Actions Section (only show when viewing a question) ---
    if st.session_state.selected_question_id is not None:
        st.markdown("---")
        st.subheader("⚡ Actions")
        
        # Get current question for button states
        question = question_service.get_question_by_id(st.session_state.selected_question_id)
        
        # Back to List button
        if st.button("⬅️ Back to List", use_container_width=True):
            st.session_state.selected_question_id = None
            # Reset question state
            st.session_state.submitted = False
            st.session_state.selected_answer = None
            st.session_state.show_explanation = False
            st.rerun()
        
        if question:
            # Favorite button
            fav_text = "⭐ Favorited" if question.is_favorite else "☆ Favorite"
            fav_type = "secondary" if question.is_favorite else "primary"
            if st.button(fav_text, type=fav_type, use_container_width=True):
                question_service.toggle_favorite(st.session_state.selected_question_id)
                st.rerun()
            
            # Mark button
            mark_text = "🚩 Marked" if question.difficult else "🏳️ Mark"
            mark_type = "secondary" if question.difficult else "primary"
            if st.button(mark_text, type=mark_type, use_container_width=True):
                question_service.toggle_marked(st.session_state.selected_question_id)
                st.rerun()

    with st.expander("ℹ️ About & Help"):
        st.info(
            """
            This application is a medical question bank viewer.

            **How to use:**
            - Use the filters above to search for questions
            - Click "View Details" to solve a question
            - Select your answer and click Submit
            - Use Actions panel to favorite or mark questions
        """
        )

# --- Custom CSS for Professional Design ---
def load_custom_css():
    """Load custom CSS for professional, dark-themed question interface"""
    css = """
    <style>
        /* === GLOBAL DARK THEME === */
        /* Hide Streamlit default elements for cleaner look */
        .stApp > header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* Force dark theme for main content area */
        .main .block-container {
            background-color: transparent !important;
            color: #FAFAFA !important;
        }
        
        /* Ensure all text is white by default */
        .stMarkdown, .stMarkdown p, .stMarkdown div {
            color: #FAFAFA !important;
        }
        
        /* === QUESTION CONTAINER === */
        /* Remove white background, keep content clean */
        .question-container {
            background: transparent !important;
            border: none !important;
            padding: 1.5rem 0;
            margin: 1rem 0;
            box-shadow: none !important;
        }
        
        /* Question text styling - white text on dark background */
        .question-text {
            line-height: 1.7;
            margin-bottom: 2rem;
            color: #FAFAFA !important;
            font-weight: 500;
            background: transparent !important;
        }
        
        .question-text p, .question-text div, .question-text span {
            color: #FAFAFA !important;
            background: transparent !important;
        }
        
        /* === CHOICE STYLING === */
        /* Base choice styling - transparent background, no border by default */
        .stRadio > div {
            gap: 0.8rem;
        }
        
        .stRadio > div > label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px;
            padding: 1rem 1.5rem;
            margin: 0.5rem 0;
            cursor: pointer;
            transition: border-color 0.2s ease-in-out;
            display: block;
            font-size: 16px;
            line-height: 1.5;
            color: #FAFAFA !important;
        }
        
        /* Subtle hover effect - only border, no background */
        .stRadio > div > label:hover {
            border-color: #4A4A4A !important;
            background: transparent !important;
        }
        
        /* Selected choice (before submission) - yellow border only */
        .stRadio > div > label:has(input:checked) {
            background: transparent !important;
            border-color: #FFC107 !important;
        }
        
        /* === POST-SUBMISSION FEEDBACK === */
        /* Correct answer - green border only, no background */
        .correct-choice {
            background: transparent !important;
            border-color: #28a745 !important;
            border-width: 2px !important;
        }
        
        /* Incorrect answer - red border only, no background */
        .incorrect-choice {
            background: transparent !important;
            border-color: #dc3545 !important;
            border-width: 2px !important;
        }
        
        /* === EXPLANATION STYLING === */
        /* Dark-themed explanation container */
        .explanation-container {
            background: #1a1c22 !important;
            border-left: 4px solid #007bff;
            border-radius: 8px;
            padding: 2rem;
            margin-top: 2rem;
            box-shadow: none;
        }
        
        .explanation-title {
            color: #007bff !important;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .explanation-content {
            line-height: 1.6;
            color: #FAFAFA !important;
            background: transparent !important;
        }
        
        .explanation-content p, .explanation-content div, .explanation-content span {
            color: #FAFAFA !important;
            background: transparent !important;
        }
        
        /* === HIDE ELEMENTS === */
        /* Hide radio button circles */
        .stRadio > div > label > div:first-child {
            display: none;
        }
        
        /* Choice text styling */
        .stRadio > div > label > div:last-child {
            margin-left: 0 !important;
            color: #FAFAFA !important;
        }
        
        /* Ensure choice text stays white */
        .stRadio > div > label > div:last-child p {
            color: #FAFAFA !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# --- Main Content Area (Remove title when viewing question) ---
if st.session_state.selected_question_id is None:
    st.title("🩺 DocuMedica Question Bank")


def display_question_list():
    """Builds a query from filters and displays a paginated list of matching questions."""
    # Build current query
    current_query = {}
    if search_query:
        current_query["text"] = search_query
    if selected_sources:
        current_query["source"] = {"$in": selected_sources}
    if selected_tags:
        current_query["tags"] = {"$in": selected_tags}
    if show_favorites_only:
        current_query["is_favorite"] = True
    if show_marked_only:
        current_query["is_marked"] = True

    # Check if query changed - if so, reset to page 1
    if current_query != st.session_state.last_query:
        st.session_state.current_page = 1
        st.session_state.last_query = current_query.copy()

    # Fetch paginated results
    try:
        result = updated_legacy_adapter.find_questions_paginated(
            current_query, 
            page=st.session_state.current_page, 
            page_size=st.session_state.page_size
        )
        
        st.session_state.question_list = result["questions"]
        st.session_state.total_questions = result["total_count"]
        total_pages = result["total_pages"]
        
    except Exception as e:
        st.error(f"Error fetching questions: {e}")
        return

    # Display results header with pagination info
    start_idx = (st.session_state.current_page - 1) * st.session_state.page_size + 1
    end_idx = min(st.session_state.current_page * st.session_state.page_size, st.session_state.total_questions)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Questions {start_idx:,}-{end_idx:,} of {st.session_state.total_questions:,}")
    with col2:
        # Page size selector
        new_page_size = st.selectbox(
            "Per page:", 
            options=[10, 20, 50, 100], 
            index=[10, 20, 50, 100].index(st.session_state.page_size),
            key="page_size_selector"
        )
        if new_page_size != st.session_state.page_size:
            st.session_state.page_size = new_page_size
            st.session_state.current_page = 1  # Reset to first page
            st.rerun()

    # Pagination controls (top)
    if total_pages > 1:
        display_pagination_controls(total_pages, "top")

    # Display questions
    if not st.session_state.question_list:
        st.info("No questions match the current filters. Try adjusting your search.")
        return

    for q in st.session_state.question_list:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                fav_icon = "⭐" if q.is_favorite else ""
                mark_icon = "🚩" if q.difficult else ""
                st.markdown(f"**{q.question_id}** {fav_icon} {mark_icon}")
                st.caption(f"Source: {q.source} | Tags: {', '.join(q.tags)}")
            with col2:
                if st.button("View Details", key=f"view_{q.question_id}"):
                    st.session_state.selected_question_id = q.question_id
                    # Reset question state when selecting new question
                    st.session_state.submitted = False
                    st.session_state.selected_answer = None
                    st.session_state.show_explanation = False
                    st.rerun()
            st.markdown("---")

    # Pagination controls (bottom)
    if total_pages > 1:
        display_pagination_controls(total_pages, "bottom")


def display_pagination_controls(total_pages, position="top"):
    """Display pagination controls with unique keys"""
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ First", disabled=(st.session_state.current_page <= 1), key=f"first_{position}"):
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("⬅️ Prev", disabled=(st.session_state.current_page <= 1), key=f"prev_{position}"):
            st.session_state.current_page -= 1
            st.rerun()
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding: 8px;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Next ➡️", disabled=(st.session_state.current_page >= total_pages), key=f"next_{position}"):
            st.session_state.current_page += 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", disabled=(st.session_state.current_page >= total_pages), key=f"last_{position}"):
            st.session_state.current_page = total_pages
            st.rerun()


def display_question_detail():
    """Displays an interactive question with sleek dark theme, instant performance, and visual-only feedback."""
    # Load custom CSS
    load_custom_css()
    
    q_id = st.session_state.selected_question_id
    
    # Core Caching Logic: Fetch from DB only if the selected question has changed
    if st.session_state.current_question_id != q_id:
        # It's a new question, so we fetch it from the database
        question = get_cached_question(q_id)
        if not question:
            st.error("Question not found!")
            st.session_state.selected_question_id = None
            return
        
        # Store the newly fetched question and its ID in the session state
        st.session_state.current_question = question
        st.session_state.current_question_id = q_id
        
        # Reset submission state for the new question
        st.session_state.submitted = False
        st.session_state.selected_answer = None
        st.session_state.show_explanation = False
    else:
        # It's the same question, just use the cached version (INSTANT!)
        question = st.session_state.current_question

    # --- Font Size Controls (now instant due to caching) ---
    col1, col2 = st.columns([10, 1])
    with col2:
        font_col1, font_col2 = st.columns(2)
        with font_col1:
            if st.button("➕", help="Increase font size", key="font_plus"):
                st.session_state.font_size = min(st.session_state.font_size + 2, 28)
                st.rerun()
        with font_col2:
            if st.button("➖", help="Decrease font size", key="font_minus"):
                st.session_state.font_size = max(st.session_state.font_size - 2, 12)
                st.rerun()

    # --- Clean Question HTML (remove all artifacts) ---
    cleaned_question_html = clean_html_content(question.question_html)
    
    # --- Question Container ---
    st.markdown(f"""
    <div class="question-container">
        <div class="question-text" style="font-size: {st.session_state.font_size}px;">
            {cleaned_question_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Interactive Choices (clean choice text) ---
    if question.choices:
        # Create choice options with cleaned text
        choice_options = []
        choice_mapping = {}
        for i, choice in enumerate(question.choices):
            # Clean choice text using the same robust cleaning function
            cleaned_choice_text = clean_html_content(choice.text)
            # Remove any remaining HTML tags and get clean text
            clean_choice_text = BeautifulSoup(cleaned_choice_text, 'html.parser').get_text(strip=True)
            choice_display = f"{choice.id}. {clean_choice_text}"
            choice_options.append(choice_display)
            choice_mapping[choice_display] = choice
        
        # Radio button for choice selection
        selected_choice_text = st.radio(
            "Choices",
            options=choice_options,
            key=f"choices_{q_id}",
            label_visibility="collapsed",
            disabled=st.session_state.submitted
        )
        
        if selected_choice_text:
            st.session_state.selected_answer = choice_mapping[selected_choice_text]

        # --- Submit Button (explanation loads instantly due to caching) ---
        if not st.session_state.submitted and st.session_state.selected_answer:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("Submit", type="primary", use_container_width=True):
                    st.session_state.submitted = True
                    st.session_state.show_explanation = True
                    st.rerun()

        # --- Visual Feedback Only (Improved Script) ---
        if st.session_state.submitted and st.session_state.selected_answer:
            # Find correct answer
            correct_choice = None
            for choice in question.choices:
                if choice.is_correct:
                    correct_choice = choice
                    break
            
            # Get clean text for comparison using robust cleaning
            correct_cleaned_text = clean_html_content(correct_choice.text)
            correct_clean_text = BeautifulSoup(correct_cleaned_text, 'html.parser').get_text(strip=True)
            selected_cleaned_text = clean_html_content(st.session_state.selected_answer.text)
            selected_clean_text = BeautifulSoup(selected_cleaned_text, 'html.parser').get_text(strip=True)
            
            # Determine if user was correct
            user_correct = st.session_state.selected_answer.is_correct
            
            # Escape quotes for JavaScript
            correct_text_escaped = correct_clean_text.replace("'", "\\'")
            selected_text_escaped = selected_clean_text.replace("'", "\\'")
            
            # Apply visual styling with improved script
            st.markdown(f"""
            <script>
                setTimeout(function() {{
                    const labels = window.parent.document.querySelectorAll('label[data-baseweb="radio"]');
                    const correctText = `{correct_choice.id}. {correct_text_escaped}`;
                    const selectedText = `{st.session_state.selected_answer.id}. {selected_text_escaped}`;
                    
                    labels.forEach(label => {{
                        const textDiv = label.querySelector('div[data-testid="stMarkdownContainer"] p');
                        if (!textDiv) return;
                        
                        const choiceText = textDiv.textContent.trim();
                        const container = label.closest('.stRadio > div > label');
                        if (!container) return;

                        // Apply correct answer styling (green border)
                        if (choiceText === correctText) {{
                            container.classList.add('correct-choice');
                        }}
                        
                        // Apply incorrect answer styling (red border) if user selected wrong
                        if (choiceText === selectedText && !{str(user_correct).lower()}) {{
                            container.classList.add('incorrect-choice');
                        }}
                    }});
                }}, 100);
            </script>
            """, unsafe_allow_html=True)

    # --- Explanation Section (loads instantly due to caching) ---
    if st.session_state.show_explanation and question.explanation_html:
        # Clean explanation HTML
        cleaned_explanation_html = clean_html_content(question.explanation_html)
        
        st.markdown("---")
        explanation_title = "💡 Explanation"
        st.markdown(f"""
        <div class="explanation-container">
            <div class="explanation-title">
                {explanation_title}
            </div>
            <div class="explanation-content" style="font-size: {st.session_state.font_size - 2}px;">
                {cleaned_explanation_html}
            </div>
        </div>
        """, unsafe_allow_html=True)


# --- Main Application Router ---
if st.session_state.selected_question_id is None:
    display_question_list()
else:
    display_question_detail()