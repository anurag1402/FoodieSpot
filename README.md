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

## Prompt Engineering Approach

The core of FoodieSpot's conversational capabilities lies in its prompt engineering. We use detailed prompts to guide the AI model (Gemini 1.5 Flash 8b) to:

-   **Understand User Intent:** Identify whether the user wants to make a reservation, modify an existing one, cancel, or ask a general question.
-   **Generate Function Calls:** Create structured function calls with relevant parameters for database interactions.
-   **Generate SQL Queries:** Translate natural language questions into safe, read-only SQL queries.
-   **Handle Date and Time:** Resolve date references like "today" and "tomorrow" and ensure consistent date formatting.
-   **Provide Context:** Include the current conversation history in the prompt to maintain context.
-   **Tool Usage:** Instruct the LLM which tools it has access to, and when to use those tools.

The prompt includes clear instructions, available tools, and examples to ensure accurate and relevant responses.

## Example Conversations

### User Journey 1: Making a Reservation

**User:** "I'd like to make a reservation for 4 at an Italian restaurant tomorrow at 7 PM."

**Agent:** "Great! What is your name?"

**User:** "John Doe."

**Agent:** "Reservation confirmed for John Doe at [Restaurant Name] on [Date] at 7 PM for 4 people. Reservation ID: [Random ID]."

### User Journey 2: Modifying a Reservation

**User:** "Can I change my reservation ID 123456 to 8 PM?"

**Agent:** "Reservation modified successfully. Reservation ID: 123456."


### User Journey 3: Asking a General Question

**User:** "How many Chinese restaurants are there?"

**Agent:** "There are 2 Chinese restaurants operated by us."

Ex:<img width="465" alt="Screenshot 2025-03-03 at 3 32 51 PM" src="https://github.com/user-attachments/assets/6df52f5b-6d1f-48b8-8ee4-ac61b24db07d" />


### User Journey 4: Getting Restaurant Recommendations

**User:** "Recommend a restaurant with a rating of 4 or higher."

**Agent:** "Recommended Restaurants: \n - **[Restaurant Name]**: [Cuisine], Rating: [Rating], Address: [Address]"

Examples:
<img width="498" alt="Screenshot 2025-03-03 at 3 29 13 PM" src="https://github.com/user-attachments/assets/11efda72-2217-493e-b50d-7674013145ba" />
<img width="540" alt="Screenshot 2025-03-03 at 3 27 46 PM" src="https://github.com/user-attachments/assets/0d964270-8541-4bf4-9d28-dbe7d8c3043c" />

## Business Strategy Summary

FoodieSpot aims to revolutionize the restaurant reservation experience by providing an intuitive and efficient AI-driven solution. Our business strategy focuses on:

1.  **Enhancing User Experience:** Delivering a seamless and personalized reservation experience through natural language interaction.
2.  **Expanding Functionality:** Continuously adding new features and integrations to meet evolving user needs.
3.  **Strategic Partnerships:** Collaborating with restaurants to offer exclusive deals and promotions.
4.  **Data-Driven Insights:** Utilizing user data to improve recommendations and optimize the reservation process.
5.  **Scalability:** Designing the platform to handle a growing user base and expand to new markets.
6. **Cost Efficiency:** Using LLM to reduce customer support and reservation handling costs.

By prioritizing user satisfaction and leveraging cutting-edge technology, FoodieSpot strives to become the leading AI restaurant reservation agent.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License.
