import streamlit as st
import streamlit.components.v1 as components
from database import db_client
import config
from question_service import question_service
from models import AssetType
from bs4 import BeautifulSoup
from database_helpers import get_image_dimensions
import re
import textwrap

# --- Initial Page Config ---
st.set_page_config(
    page_title="DocuMedica Question Bank",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Question Function ---
@st.cache_data(show_spinner="Fetching question...")
def get_cached_question(question_id):
    """Retrieves and caches the fully processed question object."""
    return question_service.get_question(question_id)


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
        # Get sources and tags directly from database
        sources = db_client.get_collection("Questions").distinct("source")
        tags = db_client.get_collection("Questions").distinct("tags")
        return sorted(sources), sorted(tags)
    except Exception as e:
        st.error(f"❌ Error fetching filter options: {e}")
        return [], []


def get_random_question_id(query):
    """Fetches a single random question ID matching the filter criteria."""
    if db_client.db is None:
        st.error("Database connection failed.")
        return None

    pipeline = [{"$match": query}, {"$sample": {"size": 1}}, {"$project": {"_id": 1}}]

    try:
        result = list(db_client.get_collection("Questions").aggregate(pipeline))
        if result:
            return result[0]["_id"]
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching random question: {e}")
        return None


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
    st.session_state.font_size = 24  # Default font size in pixels
if "selected_answer" not in st.session_state:
    st.session_state.selected_answer = None  # Tracks which choice the user selects
if "submitted" not in st.session_state:
    st.session_state.submitted = False  # Tracks if the user has submitted their answer
if "show_explanation" not in st.session_state:
    st.session_state.show_explanation = False  # Controls explanation visibility
if "asset_to_show" not in st.session_state:
    st.session_state.asset_to_show = None

# --- Question Caching for Performance ---
if "current_question" not in st.session_state:
    st.session_state.current_question = None  # Will hold the full question object
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = (
        None  # Tracks the ID of the question being displayed
    )
if "iframe_height" not in st.session_state:
    st.session_state.iframe_height = 400  # Default height for iframe

# --- Sidebar for Filters ---
with st.sidebar:
    st.title("🔍 Search & Filters")
    all_sources, all_tags = get_filter_options()

    vector_search_query = st.text_input("Free text search")
    search_query = st.text_input("Search by text in question")
    selected_sources = st.multiselect("Filter by Source", options=all_sources)
    selected_tags = st.multiselect("Filter by Tags", options=all_tags)
    st.markdown("---")
    show_favorites_only = st.checkbox("Show Favorites Only ⭐")
    show_done_only = st.checkbox("Show Done Only 🔖")

    st.markdown("---")

    if st.button("Surprise Me", use_container_width=True, type="secondary"):
        # Build the current query again, just as we do for the list view
        mongo_query = {}
        if search_query:
            search_terms = search_query.split()
            formatted_search = " ".join(['"' + term + '"' for term in search_terms])
            mongo_query["$text"] = {"$search": formatted_search}
        if selected_sources:
            mongo_query["source"] = {"$in": selected_sources}
        if selected_tags:
            mongo_query["tags"] = {"$in": selected_tags}
        if show_favorites_only:
            mongo_query["difficult"] = True
        if show_done_only:
            mongo_query["flagged"] = True
        else:
            mongo_query["flagged"] = {"$ne": True}

        # Fetch a random question ID using the current filters
        random_id = get_random_question_id(mongo_query)
        if random_id:
            # If we found a question, set it as the selected one and rerun
            st.session_state.selected_question_id = random_id
            # Reset the question state for the new question
            st.session_state.submitted = False
            st.session_state.selected_answer = None
            st.session_state.show_explanation = False
            st.rerun()
        else:
            # If no questions match the filters, show a toast message
            st.toast("No questions match the current filters!", icon="🤷‍♀️")

    # --- Actions Section (only show when viewing a question) ---
    if st.session_state.selected_question_id is not None:
        st.markdown("---")
        st.subheader("⚙️ Actions")

        # Get current question for button states
        question = question_service.get_question(st.session_state.selected_question_id)

        # Back to List button
        if st.button("⬅️ Back to List", use_container_width=True):
            st.session_state.selected_question_id = None
            # Reset question state
            st.session_state.submitted = False
            st.session_state.selected_answer = None
            st.session_state.show_explanation = False
            st.rerun()

        if question:
            # Get current status
            status = question_service.get_question_status(
                st.session_state.selected_question_id
            )
            is_favorite = status["is_favorite"]
            is_done = status["is_done"]

            # Favorite button
            fav_text = "Unfavorite ⭐" if is_favorite else "Favorite ⭐"
            if st.button(fav_text, use_container_width=True, key="toggle_favorite"):
                question_service.toggle_favorite(st.session_state.selected_question_id)
                st.rerun()

            # Done button
            done_text = "Mark as Not Done ✅" if is_done else "Mark as Done ✅"
            if st.button(done_text, use_container_width=True, key="toggle_done"):
                question_service.toggle_done(st.session_state.selected_question_id)
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
    st.title("🏥 DocuMedica Question Bank")


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
    if show_done_only:
        current_query["is_done"] = True

    # Check if query changed - if so, reset to page 1
    if current_query != st.session_state.last_query:
        st.session_state.current_page = 1
        st.session_state.last_query = current_query.copy()

    # Fetch paginated results
    try:
        # Build MongoDB query
        mongo_query = {}
        if "text" in current_query:
            # Text search in question and explanation fields
            mongo_query["$or"] = [
                {"question": {"$regex": current_query["text"], "$options": "i"}},
                {"explanation": {"$regex": current_query["text"], "$options": "i"}},
                {"name": {"$regex": current_query["text"], "$options": "i"}},
            ]
        if "source" in current_query:
            mongo_query["source"] = current_query["source"]
        if "tags" in current_query:
            mongo_query["tags"] = current_query["tags"]
        # Handle favorite filter
        if "is_favorite" in current_query:
            mongo_query["difficult"] = True

        # Handle done filter - by default exclude done questions unless specifically requested
        if "is_done" in current_query:
            mongo_query["flagged"] = True
        else:
            # By default, exclude done questions (flagged=True)
            mongo_query["flagged"] = {"$ne": True}

        # Get total count
        total_count = db_client.get_collection("Questions").count_documents(mongo_query)

        # Calculate pagination
        skip = (st.session_state.current_page - 1) * st.session_state.page_size
        total_pages = (
            total_count + st.session_state.page_size - 1
        ) // st.session_state.page_size

        # Get paginated results
        cursor = (
            db_client.get_collection("Questions")
            .find(mongo_query)
            .skip(skip)
            .limit(st.session_state.page_size)
        )
        questions = []

        for doc in cursor:
            # Create a simple question object for the list view
            question_obj = type(
                "Question",
                (),
                {
                    "question_id": doc["_id"],
                    "source": doc.get("source", ""),
                    "tags": doc.get("tags", []),
                    "is_favorite": doc.get("difficult", False),
                    "difficult": doc.get("difficult", False),
                },
            )()
            questions.append(question_obj)

        st.session_state.question_list = questions
        st.session_state.total_questions = total_count

    except Exception as e:
        st.error(f"Error fetching questions: {e}")
        return

    # Display results header with pagination info
    start_idx = (st.session_state.current_page - 1) * st.session_state.page_size + 1
    end_idx = min(
        st.session_state.current_page * st.session_state.page_size,
        st.session_state.total_questions,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(
            f"Questions {start_idx:,}-{end_idx:,} of {st.session_state.total_questions:,}"
        )
    with col2:
        # Page size selector
        new_page_size = st.selectbox(
            "Per page:",
            options=[10, 20, 50, 100],
            index=[10, 20, 50, 100].index(st.session_state.page_size),
            key="page_size_selector",
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
                mark_icon = "🔖" if q.difficult else ""
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
        if st.button(
            "⏮️ First",
            disabled=(st.session_state.current_page <= 1),
            key=f"first_{position}",
        ):
            st.session_state.current_page = 1
            st.rerun()

    with col2:
        if st.button(
            "⬅️ Prev",
            disabled=(st.session_state.current_page <= 1),
            key=f"prev_{position}",
        ):
            st.session_state.current_page -= 1
            st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>Page {st.session_state.current_page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with col4:
        if st.button(
            "Next ➡️",
            disabled=(st.session_state.current_page >= total_pages),
            key=f"next_{position}",
        ):
            st.session_state.current_page += 1
            st.rerun()

    with col5:
        if st.button(
            "Last ⏭️",
            disabled=(st.session_state.current_page >= total_pages),
            key=f"last_{position}",
        ):
            st.session_state.current_page = total_pages
            st.rerun()


def calculate_dynamic_height(html_content: str) -> int:
    """
    Calculates the required height for a Page asset by using the actual
    height of its embedded background image.
    """
    if not html_content:
        return 400  # Default height

    # Find the UUID of the background image from the <img> tag
    image_uuid_match = re.search(r'src="\[\[(.*?)\]\]"', html_content)
    if not image_uuid_match:
        # If there's no background image, return a generous default height
        return 800

    image_uuid = image_uuid_match.group(1)

    # Get the actual dimensions of the image from our helper function
    dimensions = get_image_dimensions(image_uuid)
    if not dimensions:
        # Fallback if the image file is missing or dimensions can't be read
        return 800

    # The height is the second element of the (width, height) tuple
    image_height = dimensions[1]

    # Return the image's original height plus a small buffer for any tooltips
    # that might be positioned near the bottom edge.
    return image_height + 50


def display_question_detail():
    load_custom_css()

    q_id = st.session_state.selected_question_id
    question = get_cached_question(q_id)

    if not question:
        st.error("Question not found!")
        st.session_state.selected_question_id = None
        return

    # --- Font Size Controls ---
    _, minus_col, plus_col = st.columns([0.85, 0.075, 0.075])
    with minus_col:
        if st.button("➖", help="Decrease font size", use_container_width=True):
            st.session_state.font_size = max(st.session_state.font_size - 2, 12)
            st.rerun()
    with plus_col:
        if st.button("➕", help="Increase font size", use_container_width=True):
            st.session_state.font_size = min(st.session_state.font_size + 2, 42)
            st.rerun()

    # --- Display Question Header ---
    if st.session_state.get("show_explanation", False):
        st.subheader(question.title)
    else:
        st.subheader(f"Question: {question.name}")
    st.caption(f"Source: {question.source} | Tags: {', '.join(question.tags)}")
    st.divider()

    # --- RENDER THE QUESTION BODY ---
    st.markdown(
        f"<div style='font-size: {st.session_state.font_size}px;'>{question.processed_question_html}</div>",
        unsafe_allow_html=True,
    )
    if question.primary_question_assets:
        st.write("**Associated Media:**")
        for asset in question.primary_question_assets:
            if asset.asset_type == AssetType.IMAGE:
                st.image(asset.file_path, caption=asset.name)
            elif asset.asset_type == AssetType.AUDIO:
                st.audio(asset.file_path)

    # --- INTERACTIVE CHOICES UI ---
    if question.choices:
        if not st.session_state.get("submitted", False):
            choice_options = []
            choice_mapping = {}
            for i, choice in enumerate(question.choices):
                clean_choice_text = BeautifulSoup(choice.text, "html.parser").get_text(
                    strip=True
                )
                choice_display = f"{choice.id}. {clean_choice_text}"
                choice_options.append(choice_display)
                choice_mapping[choice_display] = choice

            selected_choice_text = st.radio(
                "Choices",
                options=choice_options,
                key=f"choices_{q_id}",
                label_visibility="collapsed",
            )

            if selected_choice_text:
                st.session_state.selected_answer = choice_mapping[selected_choice_text]
        else:
            for choice in question.choices:
                clean_choice_text = BeautifulSoup(choice.text, "html.parser").get_text(
                    strip=True
                )
                border_color, border_width = "#ccc", "1px"
                if choice.is_correct:
                    border_color, border_width = "#28a745", "2px"
                elif (
                    st.session_state.selected_answer
                    and choice.id == st.session_state.selected_answer.id
                ):
                    border_color, border_width = "#dc3545", "2px"

                st.markdown(
                    f"""
                <div style=\"border: {border_width} solid {border_color}; border-radius: 10px; padding: 1rem 1.5rem; margin: 0.5rem 0;\">
                    {choice.id}. {clean_choice_text}
                </div>
                """,
                    unsafe_allow_html=True,
                )

        # --- Submit Button ---
        if not st.session_state.get("submitted", False) and st.session_state.get(
            "selected_answer"
        ):
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("Submit", type="primary", use_container_width=True):
                    st.session_state.submitted = True
                    st.session_state.show_explanation = True
                    st.rerun()

    # --- EXPLANATION AND ASSET REFERENCE DESK ---
    if st.session_state.get("show_explanation", False):
        st.divider()
        st.markdown("### Explanation")
        st.markdown(
            f"<div style='font-size: {st.session_state.font_size-2}px;'>{question.processed_explanation_html}</div>",
            unsafe_allow_html=True,
        )
        if question.primary_explanation_assets:
            st.write("**Associated Media:**")
            for asset in question.primary_explanation_assets:
                if asset.asset_type == AssetType.IMAGE:
                    st.image(asset.file_path, caption=asset.name)
                elif asset.asset_type == AssetType.AUDIO:
                    st.audio(asset.file_path)

        # --- THE ASSET REFERENCE DESK ---
        if question.inline_assets:
            st.write("**Referenced Media:**")
            for i, asset in enumerate(question.inline_assets):
                ref_cols = st.columns([0.1, 0.9])
                with ref_cols[0]:
                    st.markdown(f"**[{i+1}]**")
                with ref_cols[1]:
                    if st.button(
                        asset.link_text, key=asset.uuid, use_container_width=True
                    ):
                        st.session_state.asset_to_show = asset.uuid
                        st.rerun()

        # --- TEACHING POINTS ---
        if question.teaching_points:
            st.divider()
            st.markdown("### 🎓 Key Teaching Points")
            # Create a container for better styling
            with st.container():
                for i, point in enumerate(question.teaching_points, 1):
                    # Using custom HTML for better styling
                    st.markdown(
                        f"""
                        <div style="margin-bottom: 10px; padding: 10px; border-left: 3px solid #007bff; background-color: rgba(0, 123, 255, 0.1); border-radius: 0 8px 8px 0;">
                            <div style="display: flex; align-items: flex-start;">
                                <div style="background-color: #007bff; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0; font-size: {st.session_state.font_size-2}px; line-height: 1; text-align: center; width: 1.8em; height: 1.8em; min-width: 24px; min-height: 24px;">
                                    {i}
                                </div>
                                <div style="padding-top: 2px; font-size: {st.session_state.font_size-2}px;">
                                    {point}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # --- MODAL DISPLAY LOGIC (DIAGNOSTIC TEST) ---
    if st.session_state.asset_to_show:
        asset_id_to_show = st.session_state.asset_to_show
        asset = next(
            (a for a in question.inline_assets if a.uuid == asset_id_to_show), None
        )

        if asset:
            st.divider()
            with st.container():
                st.markdown(f"#### Viewing: {asset.link_text}")

                if asset.asset_type == AssetType.PAGE:
                    # Temporary fallback: use a large fixed height to avoid truncation
                    # This is not the final solution, but ensures content is visible
                    components.html(asset.html_content, height=1200, scrolling=False)

                elif asset.asset_type == AssetType.TABLE:
                    # Tables have a fixed, known height.
                    components.html(asset.html_content, height=600, scrolling=True)

                else:  # Handle standard Image, Audio, Video
                    if asset.asset_type == AssetType.IMAGE:
                        st.image(asset.file_path, use_column_width=True)
                    elif asset.asset_type == AssetType.AUDIO:
                        st.audio(asset.file_path)
                    elif asset.asset_type == AssetType.VIDEO:
                        st.video(asset.file_path)

                if st.button("Close Viewer", key=f"close_asset_{asset_id_to_show}"):
                    # Reset state when closing the viewer
                    st.session_state.asset_to_show = None
                    st.rerun()


# --- Main Application Router ---
if st.session_state.selected_question_id is None:
    display_question_list()
else:
    display_question_detail()
