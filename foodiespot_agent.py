
import google.generativeai as genai
import json
from foodiespot_db import recommend_restaurant, make_reservation, modify_reservation, cancel_reservation, get_reservation_details, get_connection, execute_sql_query
import streamlit as st
from datetime import date, timedelta,datetime

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-8b')

function_descriptions = [
    {
        "name": "recommend_restaurant",
        "description": "Recommends a restaurant based on user preferences.",
        "parameters": {
            "type": "object",
            "properties": {
                "cuisine": {"type": "string", "description": "The type of cuisine (e.g., Italian, Mexican)."},
                "party_size": {"type": "integer", "description": "The number of people in the party."},
                "rating": {"type": "number", "description": "Minimum restaurant rating."},
                "address": {"type": "string", "description": "The address of the user or location of interest."},
            },
        },
    },
    {
        "name": "make_reservation",
        "description": "Makes a restaurant reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_name": {"type": "string", "description": "The name of the restaurant."},
                "date": {"type": "string", "description": "The date of the reservation (DD-MM-YYYY)."},
                "time": {"type": "string", "description": "The time of the reservation (HH:MM)."},
                "party_size": {"type": "integer", "description": "The number of people in the party."},
                "customer_name": {"type": "string", "description": "The name of the person making the reservation."},
            },
            "required": ["restaurant_name", "date", "time", "party_size", "customer_name"],
        },
    },
    {
        "name": "modify_reservation",
        "description": "Modifies an existing reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "integer", "description": "The ID of the reservation."},
                "new_date": {"type": "string", "description": "The new date of the reservation (DD-MM-YYYY)."},
                "new_time": {"type": "string", "description": "The new time of the reservation (HH:MM)."},
                "new_party_size": {"type": "integer", "description": "The new number of people in the party."},
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "cancel_reservation",
        "description": "Cancels an existing reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "integer", "description": "The ID of the reservation."},
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "get_reservation_details",
        "description": "Retrieves and displays reservation details based on reservation ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "integer", "description": "The ID of the reservation."},
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "execute_sql_query",
        "description": "Executes a custom SQL query against the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The SQL query to execute."},
            },
            "required": ["query"],
        },
    },
]

def resolve_date(date_str):
    """Resolves date references like 'today', 'tomorrow', or 'DD-MM-YYYY'."""
    today = date.today()
    if date_str.lower() == "today":
        return today.strftime("%d-%m-%Y")
    elif date_str.lower() == "tomorrow":
        return (today + timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        # Handle both DD-MM-YYYY and MM-DD-YYYY formats
        try:
            # Try DD-MM-YYYY format first
            parts = date_str.split("-")
            if len(parts) == 3:
                day, month, year = map(int, parts)
                if 1 <= day <= 31 and 1 <= month <= 12:
                    return date(year, month, day).strftime("%d-%m-%Y")
            return date_str  # Return as is if it's already in correct format
        except ValueError:
            try:
                # Try MM-DD-YYYY as fallback
                month, day, year = map(int, date_str.split("-"))
                return date(year, month, day).strftime("%d-%m-%Y")
            except:
                return None

def get_top_restaurants():
    """Fetches the top 3 restaurants."""
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, cuisine, rating, address FROM restaurants ORDER BY rating DESC LIMIT 3")
        top_restaurants = cursor.fetchall()
        conn.close()
        return top_restaurants
    except Exception as e:
        conn.close()
        return f"Database error: {e}"

def generate_sql_query(user_question):
    """Generates a SQL query from a natural language question."""
    prompt = f"""
    You are an AI assistant that translates natural language questions into SQL queries.
    The database has tables:
    - restaurants (id, name, cuisine, rating, address, seating_capacity, current_booking)
    - reservations (id, restaurant_id, customer_name, date, time, party_size)
    
    The user asks: "{user_question}"
    
    Generate a safe, well-formed SQL query to answer this question. Return ONLY the SQL query without any explanations.
    Make sure it is a SELECT query only, no modification queries allowed.
    """
    
    response = model.generate_content(prompt)
    if response.text:
        # Extract SQL query, clean up any formatting
        sql_query = response.text.strip()
        # Remove any markdown code formatting
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()
        return sql_query
    return None

def is_safe_query(query):
    """Basic check to ensure query is read-only and safe."""
    query_lower = query.lower()
    unsafe_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate']
    
    # Check for unsafe keywords
    if any(keyword in query_lower.split() for keyword in unsafe_keywords):
        return False
    
    # Ensure it starts with SELECT
    if not query_lower.strip().startswith('select'):
        return False
        
    return True

def determine_intent(user_input):
    """Determine the user's intent from their input."""
    user_input_lower = user_input.lower()
    
    if any(word in user_input_lower for word in ["book", "reserve", "make a reservation"]):
        return "make_reservation"
    elif any(word in user_input_lower for word in ["change", "modify", "update", "reschedule"]) and "reservation" in user_input_lower:
        return "modify_reservation"
    elif any(word in user_input_lower for word in ["cancel", "delete"]) and "reservation" in user_input_lower:
        return "cancel_reservation"
    elif any(word in user_input_lower for word in ["recommend", "suggest", "find"]):
        return "recommend_restaurant"
    elif "details" in user_input_lower and "reservation" in user_input_lower:
        return "get_reservation_details"
    else:
        return "general_query"

def process_general_query(user_input):
    """Process a general query about restaurants or reservations."""
    # Check if this is likely a database query
    if any(word in user_input.lower() for word in ["how many", "which", "list", "show me", "what", "where", "when"]):
        sql_query = generate_sql_query(user_input)
        
        if sql_query and is_safe_query(sql_query):
            results = execute_sql_query(sql_query)
            
            if isinstance(results, list):
                if not results:
                    return "No results found for your query."
                
                # Generate a human-readable response using the model
                result_str = "\n".join([str(row) for row in results])
                interpretation_prompt = f"""
                The user asked: "{user_input}"
                
                The SQL query results are:
                {result_str}
                
                Please format these results in a human-readable way,if you dont have answers, just say "I don't have an answer for that."
                """
                
                interpretation = model.generate_content(interpretation_prompt)
                return interpretation.text
            else:
                return f"Error executing query: {results}"
        else:
            # Fall back to general conversation
            return None
    else:
        # Not a database query
        return None

def run_agent(user_input, chat_history):
    # First, check if it's a general query that needs SQL generation
    intent = determine_intent(user_input)
    
    if intent == "general_query":
        response = process_general_query(user_input)
        if response:
            return response
    
    # If not handled as a general query or SQL failed, proceed with regular function calls
    prompt = f"""
    You are a restaurant reservation agent for FoodieSpot. Your goal is to help users make, modify, or cancel reservations, and provide restaurant recommendations.

    Available Tools:
    {json.dumps(function_descriptions, indent=2)}

    Instructions:
    1. Analyze the user's input to determine their intent (reservation, modification, cancellation, recommendation, details retrieval).
    2. If the user's intent requires a tool, generate a function call with the necessary parameters.
    3. If a tool is called, execute the function and provide the result to the user.
    4. If the user's intent does not require a tool, provide a helpful response.
    5. Always ask for all required information before calling a tool.
    6. If a tool call fails, inform the user and ask them to provide correct information.
    7. When a user mentions a date, confirm the date and resolve references like 'today' or 'tomorrow' to an actual 'DD-MM-YYYY' date before calling a tool.
    8. If the user specifically states that location or rating is not an issue, or similar phrases implying any value works, then fetch the top 3 restaurants.
    9. If the user asks a general question about the restaurants, generate a SQL query to answer it.
    10. For date formats, always use DD-MM-YYYY format when calling functions.
    11.Don't ask for details at once, ask for one detail at a time.
    
    Current Conversation:
    {chat_history}

    User: {user_input}
    Agent:
    """

    response = model.generate_content(
        prompt,
        tools=[genai.types.Tool(function_declarations=function_descriptions)]
    )

    if response.candidates and response.candidates[0].content.parts:
        content = response.candidates[0].content.parts[0]
        if content.function_call:
            function_name = content.function_call.name
            arguments_dict = dict(content.function_call.args)
            arguments_json = json.dumps(arguments_dict)
            arguments = json.loads(arguments_json)

            try:
                if function_name == "recommend_restaurant":
                    result = recommend_restaurant(**arguments)
                elif function_name == "make_reservation":
                    if "date" in arguments:
                        resolved_date = resolve_date(arguments["date"])
                        if resolved_date:
                            arguments["date"] = resolved_date
                        else:
                            return "Invalid date format. Please use 'DD-MM-YYYY', 'today', or 'tomorrow'."
                    result = make_reservation(**arguments)
                elif function_name == "modify_reservation":
                    if "reservation_id" in arguments and isinstance(arguments["reservation_id"], float):
                        arguments["reservation_id"] = int(arguments["reservation_id"])
                    if "new_date" in arguments:
                        resolved_date = resolve_date(arguments["new_date"])
                        if resolved_date:
                            arguments["new_date"] = resolved_date
                        else:
                            return "Invalid date format. Please use 'DD-MM-YYYY', 'today', or 'tomorrow'."
                    result = modify_reservation(**arguments)
                elif function_name == "cancel_reservation":
                    if "reservation_id" in arguments and isinstance(arguments["reservation_id"], float):
                        arguments["reservation_id"] = int(arguments["reservation_id"])
                    result = cancel_reservation(**arguments)
                elif function_name == "get_reservation_details":
                    if "reservation_id" in arguments and isinstance(arguments["reservation_id"], float):
                        arguments["reservation_id"] = int(arguments["reservation_id"])
                    result = get_reservation_details(**arguments)
                elif function_name == "execute_sql_query":
                    query = arguments["query"]
                    if is_safe_query(query):
                        results = execute_sql_query(query)
                        if isinstance(results, list):
                            if not results:
                                return "No results found."
                            else:
                                # Format results for display
                                formatted_results = "\n".join([str(row) for row in results])
                                return formatted_results
                        else:
                            return results  # return the error message
                    else:
                        return "Sorry, I can only execute safe read-only SQL queries."
                return result
            except Exception as e:
                return f"An error occurred during function call: {e}. Please provide correct information."
        elif response.candidates[0].content.parts:
            return response.text
        else:
            return "I'm not sure how to respond to that. Could you please clarify?"
    else:
        return "I'm not sure how to respond."
