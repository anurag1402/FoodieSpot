# FoodieSpot
# FoodieSpot: AI Restaurant Reservation Agent

FoodieSpot is an AI-powered restaurant reservation agent designed to streamline the process of discovering, booking, and managing restaurant reservations. Leveraging advanced natural language processing and database integration, FoodieSpot provides a seamless user experience for finding the perfect dining experience.

## Table of Contents

-   [Features](#features)
-   [Setup Instructions](#setup-instructions)
-   [Prompt Engineering Approach](#prompt-engineering-approach)
-   [Example Conversations](#example-conversations)
-   [Business Strategy Summary](#business-strategy-summary)
-   [Contributing](#contributing)
-   [License](#license)

## Features

-   **Intelligent Restaurant Recommendations:** Receive personalized restaurant suggestions based on cuisine, party size, rating, and location.
-   **Effortless Reservations:** Make, modify, and cancel restaurant reservations through a conversational interface.
-   **Database Integration:** Seamlessly interacts with a PostgreSQL database to manage restaurant and reservation data.
-   **General Query Handling:** Answer general questions about restaurants using SQL query generation.
-   **Streamlit UI:** User-friendly web interface for easy interaction.

## Setup Instructions

1.  **Clone the Repository:**

    ```bash
    git clone [https://github.com/anurag1402/FoodieSpot.git]
    cd FoodieSpot
    ```

2.  **Create a Virtual Environment (Recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    venv\Scripts\activate  # On Windows
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Database:**

    -   Set up a PostgreSQL database and update the `foodiespot_db.py` file with your database credentials.
    -   Alternatively, for Streamlit Cloud, add the database credentials to Streamlit Secrets.

5.  **Configure Google Generative AI API:**

    -   Obtain an API key from Google Generative AI.
    -   Add the API key to Streamlit Secrets or use `.env` file for local testing.

6.  **Run the Application:**

    ```bash
    streamlit run foodiespot_streamlit.py
    ```

7.  **Deploy to Streamlit Cloud:**

    -   Push your code to a GitHub repository.
    -   Create a new app on Streamlit Cloud and link your repository.
    -   Add your database and Google API credentials to Streamlit Secrets in the app settings.



## Architecture

The application consists of three main components:

*   **Streamlit Frontend (`foodiespot_streamlit.py`):**  Provides the user interface for interacting with the application.
*   **AI Agent (`foodiespot_agent.py`):**  Handles user input, determines intent, extracts information, interacts with the LLM, and calls the appropriate database functions.
*   **Database Layer (`foodiespot_db.py`):**  Provides functions for interacting with the PostgreSQL database, including making, modifying, and canceling reservations, retrieving restaurant information, and executing SQL queries.

## Prompt Engineering

The application relies on carefully crafted prompts to guide the LLM to perform the desired tasks. Key elements of the prompt engineering approach include:

*   **Clear Intent Definition:**  The LLM is instructed to accurately identify the user's intent (e.g., making a reservation, getting recommendations).
*   **Information Extraction:**  Prompts guide the LLM to extract necessary information from user input.
*   **Tool Usage:**  The LLM is directed to use the appropriate tools (functions) to fulfill user requests.
*   **Safe Query Generation:**  When dealing with general questions, prompts ensure the LLM generates safe and accurate SQL queries.
*   **Conversational Tone:**  Prompts encourage a friendly and helpful tone in the LLM's responses.

**Example Prompts:**

Here are some  prompts used in the `foodiespot_agent.py` file:

*   **System Prompt (within `run_agent` function):**

    ```python
    prompt = f"""
    You are a restaurant reservation agent for FoodieSpot. Your goal is to help users make, modify, or cancel reservations.

    Available Tools:
    {json.dumps(function_descriptions, indent=2)}

    Instructions:
    1. Analyze the user's input and the conversation history to understand what the user wants.
    2. If the user wants to make a reservation, extract the following information from the user input: restaurant name, date (DD-MM-YYYY), time (HH:MM), party size, and customer name.
    3. Once you have extracted all the information, call the `make_reservation` tool with the extracted information.
    4. If the user wants to modify a reservation, YOU MUST call the `modify_reservation` tool.
    5. If the user wants to cancel a reservation, YOU MUST call the `cancel_reservation` tool.
    6. If the user asks for reservation details, YOU MUST call the `get_reservation_details` tool.
    7. For any other questions that are outside of the above tools, just respond politely and explain you cannot help.
    8. If any information is missing, ask the user for the missing information before calling the tool. Ask one question at a time.
    9. When asking for the date, use DD-MM-YYYY format. When asking for time, use HH:MM format.
    10. After a successful tool call, return the reservation id to the user along with a friendly confirmation message.
    11. When handling dates, confirm the date and resolve references like 'today' or 'tomorrow' to an actual 'DD-MM-YYYY' date before calling a tool.
    12. NOTE: Do NOT handle restaurant recommendations yourself - these are processed separately.

    Current Conversation:
    {chat_history}

    User: {user_input}
    Agent:
    """
    ```

*   **SQL Query Generation Prompt (within `generate_sql_query` function):**

    ```python
    prompt = f"""
    You are an AI assistant that translates natural language questions into SQL queries.
    The database has the following tables:
    - restaurants (restaurant_id INTEGER, name VARCHAR, cuisine VARCHAR, rating FLOAT, address TEXT, seating_capacity INTEGER, current_booking INTEGER)
    - reservations (reservation_id INTEGER, restaurant_id INTEGER, customer_name VARCHAR, date DATE, time TIME, party_size INTEGER)

    The user asks: "{user_question}"

    Generate a safe, well-formed SQL query to answer this question about restaurants or reservations. Return ONLY the SQL query without any explanations.
    Make sure it is a SELECT query only, no modification queries allowed.
    """
    ```

*   **Recommendation Interpretation Prompt (within `process_general_query` function):**

    ```python
    interpretation_prompt = f"""
    The user asked for a recommendation: "{user_input}"

    The database query returned these results:
    {result_str}

    Please format these as restaurant recommendations in a conversational style.
    Highlight the restaurant name, cuisine type, rating, and location.
    DO NOT ask for additional information like area, date or time preferences.
    DO NOT ask any follow-up questions.
    Just provide the recommendations directly.
    """
    ```

These prompts are designed to guide the LLM in understanding user requests, extracting relevant information, and generating appropriate responses.

## Business Strategy

FoodieSpot aims to provide a seamless and personalized restaurant experience. The core elements of the business strategy are:

*   **AI-Powered Convenience:** Simplify the restaurant search and reservation process using AI.
*   **Personalized Recommendations:**  Offer tailored recommendations based on user preferences.
*   **Comprehensive Restaurant Information:** Provide detailed information about restaurants.
*   **Efficient Reservation Management:**  Enable users to easily manage their reservations.
*   **24/7 Availability:**  Provide a 24/7 AI assistant.



## Assumptions

*   The database contains accurate and up-to-date information.
*   The LLM accurately understands user intent.
*   Users are comfortable interacting with an AI assistant.
*   A stable internet connection is available.
*   The Google Gemini API remains available and affordable.

## Limitations

*   **Database Size:**  Effectiveness depends on the size and quality of the restaurant database.
*   **Language Understanding:**  The LLM may struggle with complex or ambiguous requests.
*   **Error Handling:**  Unexpected errors may occur.
*   **Scalability:**  Scalability may be limited by the database and LLM API.
*   **Security:**  Vulnerable to security risks (e.g., SQL injection) if not properly secured.
*   **LLM Cost:** The cost of using the LLM API could be a limiting factor.

## Future Enhancements

*   **Improved Intent Detection:**  Implement more sophisticated intent detection algorithms.
*   **Contextual Awareness:**  Improve the LLM's ability to understand conversation context.
*   **Multi-Lingual Support:**  Add support for multiple languages.
*   **Integration with Mapping Services:**  Integrate with mapping services for directions.
*   **User Reviews and Ratings:**  Add user reviews and ratings.
*   **Image Recognition:**  Allow users to search based on photos of food or ambiance.
*   **Real-Time Availability Updates:**  Integrate with restaurant systems for real-time availability.
*   **Automated Seating Management:**  Develop an automated seating management system.


## Example Conversations

### User Journey 1: Making a Reservation
<img width="310" alt="Screenshot 2025-03-03 at 5 01 32 PM" src="https://github.com/user-attachments/assets/fa598fa7-0126-4185-a9e7-6b07eb504465" />



### User Journey 2: Modifying a Reservation

<img width="516" alt="Screenshot 2025-03-03 at 4 48 04 PM" src="https://github.com/user-attachments/assets/4f530be7-126b-422b-b853-ba1b3c812cb8" />

<img width="475" alt="Screenshot 2025-03-03 at 4 49 15 PM" src="https://github.com/user-attachments/assets/99ec8eee-4afa-47c0-bede-616d27daf107" />



### User Journey 3: Asking a General Question

**User:** "How many Chinese restaurants are there?"

**Agent:** "There are 2 Chinese restaurants operated by us."

Ex:
<img width="465" alt="Screenshot 2025-03-03 at 3 32 51 PM" src="https://github.com/user-attachments/assets/6df52f5b-6d1f-48b8-8ee4-ac61b24db07d" />


### User Journey 4: Getting Restaurant Recommendations

<img width="498" alt="Screenshot 2025-03-03 at 3 29 13 PM" src="https://github.com/user-attachments/assets/11efda72-2217-493e-b50d-7674013145ba" />

<img width="540" alt="Screenshot 2025-03-03 at 3 27 46 PM" src="https://github.com/user-attachments/assets/0d964270-8541-4bf4-9d28-dbe7d8c3043c" />

#


