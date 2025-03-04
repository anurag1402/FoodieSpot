
import google.generativeai as genai
import json
from foodiespot_db import recommend_restaurant, make_reservation, modify_reservation, cancel_reservation, get_reservation_details, get_connection, execute_sql_query
import streamlit as st
from datetime import date, timedelta,datetime

import re



GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-8b')

unction_descriptions = [
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

def determine_intent(user_input):
    """Determine user intent using keywords but prioritize recommendation requests"""
    user_input_lower = user_input.lower()
    
    # First check for recommendation keywords
    recommendation_keywords = ["recommend", "suggestion", "best", "top", "good", "popular"]
    if any(keyword in user_input_lower for keyword in recommendation_keywords):
        return "RECOMMENDATION"
        
    # Then check for other reservation actions
    if any(word in user_input_lower for word in ["book", "reserve", "make reservation"]):
        return "MAKE_RESERVATION"
    elif any(word in user_input_lower for word in ["change", "modify", "update", "reschedule"]):
        return "MODIFY_RESERVATION"
    elif any(word in user_input_lower for word in ["cancel", "delete"]):
        return "CANCEL_RESERVATION"
    elif any(word in user_input_lower for word in ["show", "view", "get", "details", "find"]) and "reservation" in user_input_lower:
        return "GET_RESERVATION_DETAILS"
    elif any(word in user_input_lower for word in ["how many", "which", "list", "show", "what", "where", "when"]):
        return "DATABASE_QUERY"
    else:
        return "OTHER"

def generate_sql_query(user_question):
    """Generates a SQL query from a natural language question."""
    # For recommendation queries, enhance the query generation with specific structure
    if "recommend" in user_question.lower() or "suggestion" in user_question.lower():
        # Extract cuisine type and rating if mentioned
        cuisine_types = ["italian", "mexican", "chinese", "indian", "japanese", "american", "french", "thai", "greek", "spanish"]
        cuisine_type = None
        for cuisine in cuisine_types:
            if cuisine in user_question.lower():
                cuisine_type = cuisine.capitalize()
                break
        
        # Check for rating requirements
        rating_match = re.search(r'rating\s*(of|above|over)?\s*([0-9.]+)', user_question.lower())
        rating_threshold = None
        if rating_match:
            rating_threshold = float(rating_match.group(2))
        
        # Construct appropriate SQL query based on extracted parameters
        if cuisine_type and rating_threshold:
            return f"SELECT name, cuisine, rating, address FROM restaurants WHERE cuisine = '{cuisine_type}' AND rating >= {rating_threshold} ORDER BY rating DESC"
        elif cuisine_type:
            return f"SELECT name, cuisine, rating, address FROM restaurants WHERE cuisine = '{cuisine_type}' ORDER BY rating DESC"
        elif rating_threshold:
            return f"SELECT name, cuisine, rating, address FROM restaurants WHERE rating >= {rating_threshold} ORDER BY rating DESC"
        else:
            return "SELECT name, cuisine, rating, address FROM restaurants ORDER BY rating DESC LIMIT 5"
    
    # For general queries, use the LLM
    prompt = f"""
    You are an AI assistant that translates natural language questions into SQL queries.
    The database has the following tables:
    - restaurants (restaurant_id INTEGER, name VARCHAR, cuisine VARCHAR, rating FLOAT, address TEXT, seating_capacity INTEGER, current_booking INTEGER)
    - reservations (reservation_id INTEGER, restaurant_id INTEGER, customer_name VARCHAR, date DATE, time TIME, party_size INTEGER)

    The user asks: "{user_question}"
    
    Generate a safe, well-formed SQL query to answer this question about restaurants or reservations. Return ONLY the SQL query without any explanations.
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

def process_general_query(user_input):
    """Process a general query about restaurants or reservations, including recommendations."""
    # Determine if this is a recommendation request based on keywords
    is_recommendation = any(word in user_input.lower() for word in ["recommend", "suggestion", "best", "top", "good", "popular"])
    
    # Generate appropriate SQL query
    sql_query = generate_sql_query(user_input)
    
    if sql_query and is_safe_query(sql_query):
        results = execute_sql_query(sql_query)
        
        if isinstance(results, list):
            if not results:
                return "I don't have any restaurants that match your criteria at the moment."
            
            # Generate a human-readable response using the model
            result_str = "\n".join([str(row) for row in results])
            
            # Use different prompt for recommendations vs. general queries
            if is_recommendation:
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
            else:
                interpretation_prompt = f"""
                The user asked: "{user_input}"
                
                The database query returned these results:
                {result_str}
                
                Format these results in a conversational, helpful way.
                DO NOT ask for additional information.
                DO NOT ask any follow-up questions.
                """
            
            interpretation = model.generate_content(interpretation_prompt)
            return interpretation.text
        else:
            return "I couldn't find any restaurants matching your criteria at the moment."
    else:
        # Fall back to a default response for recommendations
        if is_recommendation:
            default_query = "SELECT name, cuisine, rating, address FROM restaurants ORDER BY rating DESC LIMIT 5"
            results = execute_sql_query(default_query)
            
            if isinstance(results, list) and results:
                result_str = "\n".join([str(row) for row in results])
                
                interpretation_prompt = f"""
                The user asked for a recommendation: "{user_input}"
                
                Since I couldn't create a specific query, here are our top-rated restaurants:
                {result_str}
                
                Please format these as restaurant recommendations in a conversational style.
                DO NOT ask for additional information like area, date or time preferences.
                DO NOT ask any follow-up questions.
                Just provide the recommendations directly.
                """
                
                interpretation = model.generate_content(interpretation_prompt)
                return interpretation.text
        
        return None

def run_agent(user_input, chat_history):
    # Determine user intent directly based on input text
    intent = determine_intent(user_input)
    
    # For restaurant recommendations, ALWAYS process directly through the general query function
    if intent == "RECOMMENDATION":
        general_response = process_general_query(user_input)
        if general_response:
            return general_response
        # Even if process_general_query returns None, don't proceed to the LLM for recommendations
        return "I'm sorry, I couldn't find any restaurants matching your criteria at the moment."
    
    # For database queries, try process_general_query first
    if intent == "DATABASE_QUERY":
        general_response = process_general_query(user_input)
        if general_response:
            return general_response

    # For other intents, use the LLM with function calling
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
                # Execute the appropriate function based on the function call
                if function_name == "make_reservation":
                    # Resolve date if provided
                    if "date" in arguments:
                        resolved_date = resolve_date(arguments["date"])
                        if resolved_date:
                            arguments["date"] = resolved_date
                        else:
                            return "Invalid date format. Please use 'DD-MM-YYYY', 'today', or 'tomorrow'."
                    
                    result = make_reservation(**arguments)
                    if isinstance(result, dict) and 'error' not in result:
                        confirmation_message = f"Reservation confirmed! Your reservation ID is {result['reservation_id']}"
                        return result  # Return the whole dictionary
                    return result
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
                    return result
                elif function_name == "cancel_reservation":
                    if "reservation_id" in arguments and isinstance(arguments["reservation_id"], float):
                        arguments["reservation_id"] = int(arguments["reservation_id"])
                    result = cancel_reservation(**arguments)
                    return result
                elif function_name == "get_reservation_details":
                    if "reservation_id" in arguments and isinstance(arguments["reservation_id"], float):
                        arguments["reservation_id"] = int(arguments["reservation_id"])
                    result = get_reservation_details(**arguments)
                    return result
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
                        return "The provided query appears to be unsafe and cannot be executed."
                else:
                    return f"I do not recognize this tool. Function name: {function_name}"
            except Exception as e:
                return f"An error occurred during function call: {e}. Please provide correct information."
        elif response.candidates[0].content.parts:
            # If the model responds without a tool
            return response.text
        else:
            return "I'm not sure how to respond. Could you please clarify?"
