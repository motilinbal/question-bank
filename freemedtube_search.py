import streamlit as st
from pymongo import MongoClient
import re
from urllib.parse import quote
from fuzzywuzzy import fuzz, process

# Page configuration
st.set_page_config(
    page_title="Medical Video Search",
    page_icon="🔍",
    layout="wide"
)

# MongoDB Connection
@st.cache_resource
def get_database():
    """Initialize MongoDB connection"""
    try:
        CONNECTION_STRING = "mongodb://localhost:27017/"
        client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client['freemedtube']['courses']
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        st.stop()

collection = get_database()

# Super fast search function
@st.cache_data(ttl=300)  # Cache for 5 minutes
def search_videos(query, limit=100):
    """Lightning fast search with fuzzy matching"""
    if not query or len(query.strip()) < 2:
        return []
    
    # Escape regex special characters
    escaped_query = re.escape(query.strip())
    
    # Optimized aggregation pipeline
    pipeline = [
        # First match - use text index for speed
        {"$match": {"$text": {"$search": query}}},
        
        # Unwind and filter in one go
        {"$unwind": "$chapters"},
        {"$unwind": "$chapters.videos"},
        
        # Secondary filter on video titles
        {"$match": {"chapters.videos.title": {"$regex": escaped_query, "$options": "i"}}},
        
        # Project only what we need
        {"$project": {
            "_id": 0,
            "course_title": 1,
            "chapter_title": "$chapters.chapter_title",
            "video_title": "$chapters.videos.title",
            "video_url": "$chapters.videos.url",
            "base_url": 1,
            "score": {"$meta": "textScore"}
        }},
        
        # Sort by relevance and limit
        {"$sort": {"score": -1}},
        {"$limit": limit}
    ]
    
    try:
        results = list(collection.aggregate(pipeline))
        
        # Clean URLs and apply fuzzy matching
        cleaned_results = []
        for result in results:
            # Clean URL
            base_url = result.get('base_url', 'https://freemedtube.net/')
            video_url = result['video_url']
            
            if video_url.startswith('http'):
                clean_url = video_url
            else:
                clean_url = f"{base_url.rstrip('/')}/{video_url.lstrip('/')}"
            
            # Fix double slashes and encode spaces
            clean_url = re.sub(r'(?<!:)/+', '/', clean_url)
            if '://' in clean_url:
                protocol_domain, path = clean_url.split('://', 1)
                if '/' in path:
                    domain, file_path = path.split('/', 1)
                    encoded_path = quote(file_path, safe='/')
                    result['video_url'] = f"{protocol_domain}://{domain}/{encoded_path}"
                else:
                    result['video_url'] = clean_url
            
            # Clean title
            clean_title = result['video_title']
            clean_title = re.sub(r'\s*-\s*.*from.*on Vimeo.*$', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\s*Kenhub-.*$', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'_', ' ', clean_title)
            result['clean_title'] = clean_title.strip()
            
            cleaned_results.append(result)
        
        # Apply enhanced fuzzy matching for better results
        if cleaned_results and len(query) > 3:
            try:
                # Enhanced fuzzy match on full context (course + chapter + title)
                fuzzy_results = process.extract(
                    query.strip().lower(), 
                    cleaned_results, 
                    processor=lambda x: f"{x['course_title']} {x['chapter_title']} {x['clean_title']}".lower(),
                    scorer=fuzz.token_sort_ratio,
                    limit=limit
                )
                # Higher threshold for better precision
                filtered_results = [result[0] for result in fuzzy_results if result[1] > 70]
                return filtered_results[:limit]
            except:
                # Fallback to original results if fuzzy matching fails
                pass
        
        return cleaned_results
        
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

# Get accurate stats
@st.cache_data(ttl=3600)
def get_accurate_stats():
    """Get exact database stats via aggregation"""
    try:
        total_courses = collection.count_documents({})
        
        # Exact video count via aggregation
        pipeline = [
            {"$project": {
                "video_count": {"$sum": {"$map": {
                    "input": "$chapters",
                    "as": "chapter",
                    "in": {"$size": "$$chapter.videos"}
                }}}
            }},
            {"$group": {
                "_id": None,
                "total_videos": {"$sum": "$video_count"}
            }}
        ]
        
        result = list(collection.aggregate(pipeline))
        total_videos = result[0]['total_videos'] if result else 0
        
        return {"courses": total_courses, "videos": total_videos}
    except Exception as e:
        return {"courses": "Unknown", "videos": "Unknown"}

# Initialize session state for recent searches
if 'recent_searches' not in st.session_state:
    st.session_state.recent_searches = []

# Main App
st.title("🔍 Medical Video Search")
st.markdown("*Fast, fuzzy search across 30,000+ medical education videos*")

# Accurate stats
stats = get_accurate_stats()
col1, col2 = st.columns(2)
with col1:
    st.metric("Courses", stats["courses"])
with col2:
    st.metric("Videos", stats["videos"])

st.divider()

# Search interface
st.subheader("Search Medical Videos")

# Main search bar
search_query = st.text_input(
    "🔍 Enter search terms",
    placeholder="e.g., cranial nerve, cardiology, anatomy, pharmacology...",
    help="Search across video titles, courses, and chapters. Supports fuzzy matching for typos."
)

# Recent searches (above search bar for better visibility)
if st.session_state.recent_searches:
    recent = st.selectbox(
        "Recent searches:",
        [""] + st.session_state.recent_searches[-10:],
        help="Select a recent search to reuse"
    )
    if recent and recent != search_query:
        search_query = recent
        st.rerun()

# Search options
max_results = st.selectbox("Max results:", [50, 100, 200, 500], index=1)

# Perform search
if search_query:
    # Add to recent searches
    if search_query not in st.session_state.recent_searches:
        st.session_state.recent_searches.append(search_query)
        st.session_state.recent_searches = st.session_state.recent_searches[-10:]
    
    # Search with spinner
    with st.spinner("Searching..."):
        results = search_videos(search_query, max_results)
    
    if results:
        # Results header with ARIA announcement
        st.markdown(f'<div aria-live="polite">Found {len(results)} videos matching \'{search_query}\'</div>', unsafe_allow_html=True)
        
        # Suggest broadening if few results
        if len(results) < 5:
            st.info("💡 Few results found—try broader terms or synonyms like 'cerebral' for 'brain', 'cardiac' for 'heart'")
        
        # Sort options
        sort_by = st.radio("Sort by:", ["Relevance", "Course", "Title"], horizontal=True)
        
        if sort_by == "Course":
            results.sort(key=lambda x: (x['course_title'], x['chapter_title'], x['clean_title']))
        elif sort_by == "Title":
            results.sort(key=lambda x: x['clean_title'])
        
        st.divider()
        
        # Group results by course for better context
        from collections import defaultdict
        grouped = defaultdict(list)
        for result in results:
            grouped[result['course_title']].append(result)
        
        # Display grouped results
        for course_title, videos in grouped.items():
            with st.expander(f"📚 {course_title} ({len(videos)} videos)", expanded=len(grouped) <= 3):
                for i, video in enumerate(videos, 1):
                    # Main link
                    st.markdown(f"**{i}. [{video['clean_title']}]({video['video_url']})**")
                    
                    # Chapter context
                    st.caption(f"📑 {video['chapter_title']}")
                    
                    # Copy link (collapsed by default)
                    with st.expander("🔗 Copy URL", expanded=False):
                        st.code(video['video_url'])
                    
                    if i < len(videos):  # Don't add divider after last item in group
                        st.divider()
    
    else:
        st.warning(f"No results found for '{search_query}'")
        st.info("""
        **Search Tips:**
        - Try broader terms (e.g., 'heart' instead of 'myocardial infarction')
        - Check spelling (fuzzy search helps but isn't perfect)
        - Use medical synonyms (e.g., 'brain' or 'cerebral')
        - Try single keywords first, then combine
        """)

else:
    # No search - show helpful info
    st.info("""
    **Welcome to Medical Video Search!**
    
    🔍 **Features:**
    - Search across 30,000+ medical education videos
    - Fuzzy matching handles typos automatically
    - Fast results from indexed database
    - Clean, clickable links to all videos
    
    💡 **Search Examples:**
    - `cranial nerve` - Find all cranial nerve videos
    - `cardio` - Find cardiology content
    - `pharm` - Find pharmacology content
    
    Just start typing in the search box above!
    """)

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Medical Video Search | Powered by MongoDB + Fuzzy Search<br>
        Fast search across medical education content from freemedtube.net
    </div>
    """,
    unsafe_allow_html=True
)