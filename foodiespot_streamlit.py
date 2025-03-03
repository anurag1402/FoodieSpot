import streamlit as st
from foodiespot_agent import run_agent
from foodiespot_db import get_connection
import time
import random

# Page configuration
st.set_page_config(
    page_title="FoodieSpot",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

try:
    local_css("style.css")
except FileNotFoundError:
    st.warning("style.css file not found. Some styling may be missing.")

# Custom header with logo
def render_header():
    st.markdown(
        """
        <div class="app-header">
            <span style="font-size: 40px;">🍔</span>
            <h1>FoodieSpot</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

# Sidebar with animation
st.sidebar.markdown('<div class="sidebar-header">🍔 FoodieSpot</div>', unsafe_allow_html=True)
st.sidebar.markdown('---')
st.sidebar.markdown('### Navigation')

page = st.sidebar.radio("", ("💬 Chat with Assistant", "🍽️ Top Restaurants", "ℹ️ About"))

# Add some additional sidebar elements for visual appeal
st.sidebar.markdown('---')


# Main content
if page == "💬 Chat with Assistant":
    render_header()
    st.markdown("<h2>Your Personal Restaurant Assistant</h2>", unsafe_allow_html=True)

    # Chat container with styling
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.chat_history = ""
        # Add a welcome message
        welcome_message = "👋 Hello! I'm your FoodieSpot assistant. I can help you find restaurants, make reservations, or answer questions about cuisines. How can I assist you today?"
        st.session_state.messages.append({"role": "assistant", "content": welcome_message})

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input with custom styling
    prompt = st.chat_input("What would you like to know about restaurants?")

    if prompt:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Rerun to display user message
        st.rerun()

elif page == "🍽️ Top Restaurants":
    render_header()
    st.markdown("<h2>Top-Rated Restaurants</h2>", unsafe_allow_html=True)

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT cuisine FROM restaurants")
            cuisines = [cuisine[0] for cuisine in cursor.fetchall()]

            # Add visual elements
            st.markdown("""
            <div style="background-color: #fff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            """, unsafe_allow_html=True)

            selected_cuisine = st.selectbox("What cuisine are you craving today?", cuisines)

            cursor.execute("SELECT name, cuisine, rating, address FROM restaurants WHERE cuisine = %s ORDER BY rating DESC LIMIT 5", (selected_cuisine,))
            top_restaurants = cursor.fetchall()

            if top_restaurants:
                st.markdown(f"<h3>Top {selected_cuisine} Restaurants</h3>", unsafe_allow_html=True)
                st.markdown('<div class="restaurant-list">', unsafe_allow_html=True)

                for name, cuisine, rating, address in top_restaurants:
                    # Generate stars based on rating
                    stars = "★" * int(rating) + "☆" * (5 - int(rating))

                    st.markdown(f"""
                    <div class="restaurant-card">
                        <div class="restaurant-name">{name}</div>
                        <div class="restaurant-rating">Rating: {rating}/5 <span class="rating-stars">{stars}</span></div>
                        <div>{address}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info(f"No restaurants found for {selected_cuisine}.")

            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error fetching restaurants: {e}")
        finally:
            conn.close()
    else:
        st.error("Database connection failed. Cannot display restaurants.")

elif page == "ℹ️ About":
    render_header()
    st.markdown("<h2>About FoodieSpot</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #fff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
    <h3>Our Mission</h3>
    <p>FoodieSpot is dedicated to connecting food lovers with their perfect dining experiences.
        Our AI-powered platform makes restaurant discovery and reservations effortless.</p>

    <h3>How It Works</h3>
    <p>Simply chat with our assistant to find restaurants, get recommendations, or make reservations.
    Our system uses advanced AI to understand your preferences and provide personalized suggestions.</p>

    <h3>Features</h3>
    <ul>
    <li><strong>Smart Recommendations</strong> - Get personalized restaurant suggestions</li>
    <li><strong>Easy Reservations</strong> - Book tables without leaving the app</li>
    <li><strong>Cuisine Explorer</strong> - Discover top restaurants by cuisine type</li>
    <li><strong>24/7 Assistance</strong> - Our AI assistant is always available</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


# Callback for handling messages in chat page
def animated_loading():
    def animated_loading():
        with st.spinner('Thinking...'):
            time.sleep(1.5)


# Use in the chat response section:
if page == "💬 Chat with Assistant" and len(st.session_state.messages) > 0 and \
        st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        animated_loading()  # Add visual feedback
        user_message = st.session_state.messages[-1]["content"]
        full_response = run_agent(user_message, st.session_state.chat_history)

        if isinstance(full_response, str):  # Handle string responses
            message_placeholder.markdown(full_response)
        elif isinstance(full_response, dict):  # Handle dictionary responses
            details = f"""
            **Reservation Details:**
            - Reservation ID: {full_response.get('reservation_id')}
            - Restaurant: {full_response.get('restaurant_name')}
            - Customer: {full_response.get('customer_name')}
            - Date: {full_response.get('date')}
            - Time: {full_response.get('time')}
            - Party Size: {full_response.get('party_size')}
            """
            message_placeholder.markdown(details)
        elif full_response is None:  # Handle None response
            message_placeholder.markdown("Reservation not found.")
        else:  # handle unexpected response.
            message_placeholder.markdown("An unexpected error occurred.")

        st.session_state.chat_history += f"User: {user_message}\nAgent: {full_response}\n"
        st.session_state.messages.append(
            {"role": "assistant",
             "content": message_placeholder.markdown(details) if isinstance(full_response, dict) else full_response})

# Add footer
st.markdown("""
<footer>
    <p>Anurag A</p>

</footer>
""", unsafe_allow_html=True)
