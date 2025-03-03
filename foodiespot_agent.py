
import google.generativeai as genai
import json
from foodiespot_db import recommend_restaurant, make_reservation, modify_reservation, cancel_reservation, get_reservation_details, get_connection, execute_sql_query
import streamlit as st
from datetime import date, timedelta
import re

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
        return 
def create_conversation_context():
    """Creates a new conversation context dictionary to track conversation state."""
    return {
        "current_restaurant": None,        # Remembers which restaurant the user is discussing
        "current_cuisine": None,           # Tracks cuisine preference mentioned previously
        "current_party_size": None,        # Stores party size once mentioned
        "current_date": None,              # Keeps track of the reservation date
        "current_time": None,              # Keeps track of the reservation time
        "current_customer_name": None,     # Remembers customer name once provided
        "current_reservation_id": None,    # Tracks reservation ID for modifications/cancellations
        "last_intent": None,               # Remembers what the user was trying to do
        "recommendations": [],             # Stores list of recent restaurant recommendations
        "pending_info": []                 # Tracks what information we still need to collect
    }

def update_context_from_input(user_input, context):
    """Extracts relevant information from user input and updates the conversation context."""
    user_input_lower = user_input.lower()
    
    # Extract restaurant name - look for patterns like "at [restaurant name]" or "book [restaurant name]"
    restaurant_patterns = [
        r"(?:at|in|for|book|reserve|to|from)\s+([A-Z][A-Za-z\s']+)(?:\s+for|on|at|tomorrow|today|restaurant|\.|$)",
        r"([A-Z][A-Za-z\s']+)(?:\s+restaurant)"
    ]
    
    for pattern in restaurant_patterns:
        match = re.search(pattern, user_input)
        if match and len(match.group(1)) > 2:  # Ensure it's not just a short word
            potential_restaurant = match.group(1).strip()
            # Avoid setting common words like "today" or "tomorrow" as restaurant names
            if potential_restaurant.lower() not in ["today", "tomorrow", "restaurant", "reservation", "dinner", "lunch"]:
                context["current_restaurant"] = potential_restaurant
                break
    
    # Extract cuisine preferences
    cuisine_pattern = r"(?:like|prefer|want|looking for|find|suggest|recommend)\s+(?:some|a)?\s*([A-Za-z]+)(?:\s+food|cuisine)"
    match = re.search(cuisine_pattern, user_input_lower)
    if match:
        context["current_cuisine"] = match.group(1).strip()
    
    # Extract party size - match numbers followed by "people" or "persons" or similar
    party_size_pattern = r"(\d+)\s+(?:people|persons|guests|diners|party size|party of)"
    match = re.search(party_size_pattern, user_input_lower)
    if match:
        context["current_party_size"] = int(match.group(1))
    
    # Extract date
    date_patterns = [
        r"(?:on|for)\s+(today|tomorrow)",
        r"(?:on|for)\s+(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))",
        r"(?:on|for)\s+(?:the\s+)?(\d{1,2}-\d{1,2}-\d{4})"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            date_str = match.group(1)
            resolved_date = resolve_date(date_str)
            if resolved_date:
                context["current_date"] = resolved_date
            break
                
    # Extract time
    time_pattern = r"(?:at|for|by)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|midnight|\d{1,2}\s*o'clock)"
    match = re.search(time_pattern, user_input_lower)
    if match:
        time_str = match.group(1)
        # Convert to 24-hour format
        if "am" in time_str.lower() or "pm" in time_str.lower():
            try:
                # Try to parse the time
                time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
                context["current_time"] = time_obj.strftime("%H:%M")
            except ValueError:
                try:
                    # Try without minutes
                    time_obj = datetime.strptime(time_str.strip(), "%I %p")
                    context["current_time"] = time_obj.strftime("%H:%M")
                except ValueError:
                    pass
        elif ":" in time_str:
            # Assume 24-hour format
            try:
                time_obj = datetime.strptime(time_str.strip(), "%H:%M")
                context["current_time"] = time_obj.strftime("%H:%M")
            except ValueError:
                pass
    
    # Extract customer name - this is trickier and might need multiple patterns
    name_patterns = [
        r"(?:name is|for)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        r"(?:reservation for|under|booking for)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, user_input)
        if match:
            context["current_customer_name"] = match.group(1).strip()
            break
    
    # Extract reservation ID
    id_pattern = r"(?:reservation|booking|confirmation)\s+(?:id|number|#)\s*(?:is|:)?\s*(\d{4,6})"
    match = re.search(id_pattern, user_input_lower)
    if match:
        context["current_reservation_id"] = int(match.group(1))
    
    # Just digits pattern - might be a reservation ID
    if context["last_intent"] in ["modify_reservation", "cancel_reservation", "get_reservation_details"]:
        digits_pattern = r"^(\d{4,6})$"
        match = re.search(digits_pattern, user_input.strip())
        if match:
            context["current_reservation_id"] = int(match.group(1))
    
    return context

def get_next_required_info(context, intent):
    """Determines what information is still needed based on intent and context."""
    # Reset pending info list
    context["pending_info"] = []
    
    if intent == "make_reservation":
        required_fields = {
            "current_restaurant": "Which restaurant would you like to book?",
            "current_date": "For what date would you like to make the reservation?",
            "current_time": "At what time would you like to reserve?",
            "current_party_size": "How many people will be in your party?",
            "current_customer_name": "What name should I put the reservation under?"
        }
        
        for field, question in required_fields.items():
            if context[field] is None:
                context["pending_info"].append((field, question))
    
    elif intent == "modify_reservation":
        if context["current_reservation_id"] is None:
            context["pending_info"].append(("current_reservation_id", "What is your reservation ID number?"))
        else:
            # Only ask for fields the user wants to modify
            possible_fields = {
                "current_date": "What date would you like to change the reservation to?",
                "current_time": "What time would you like to change the reservation to?",
                "current_party_size": "How many people will be in your party now?"
            }
            
            # We need at least one field to modify
            if all(context[field] is None for field in ["current_date", "current_time", "current_party_size"]):
                context["pending_info"].append(("modification_field", "What would you like to change about your reservation? The date, time, or party size?"))
    
    elif intent == "cancel_reservation" or intent == "get_reservation_details":
        if context["current_reservation_id"] is None:
            context["pending_info"].append(("current_reservation_id", "What is your reservation ID number?"))
    
    elif intent == "recommend_restaurant":
        # For recommendations, we'll be more flexible - no required fields but we'll use what we have
        pass
    
    return context["pending_info"]


def run_agent(user_input, chat_history):
    # Initialize or retrieve conversation context
    if "conversation_context" not in globals():
        globals()["conversation_context"] = create_conversation_context()
    
    context = globals()["conversation_context"]
    
    # First, update context with any information from the user's input
    context = update_context_from_input(user_input, context)
    
    # Determine intent
    intent = determine_intent(user_input)
    context["last_intent"] = intent
    
    # Get next required information based on intent and current context
    pending_info = get_next_required_info(context, intent)
    
    # Check if we're waiting for specific information
    if pending_info:
        # Ask for the next piece of information in the sequence
        field, question = pending_info[0]
        return question
    
    # If we have all required information, proceed with the appropriate function call
    if intent == "make_reservation" and all(context[field] is not None for field in ["current_restaurant", "current_date", "current_time", "current_party_size", "current_customer_name"]):
        # We have all required info, make the reservation
        result = make_reservation(
            restaurant_name=context["current_restaurant"],
            date=context["current_date"],
            time=context["current_time"],
            party_size=context["current_party_size"],
            customer_name=context["current_customer_name"]
        )
        
        # Reset context for the next conversation
        globals()["conversation_context"] = create_conversation_context()
        return result
    
    elif intent == "modify_reservation" and context["current_reservation_id"] is not None:
        # Create arguments dictionary with only the fields that are provided
        mod_args = {"reservation_id": context["current_reservation_id"]}
        
        if context["current_date"] is not None:
            mod_args["new_date"] = context["current_date"]
        if context["current_time"] is not None:
            mod_args["new_time"] = context["current_time"]
        if context["current_party_size"] is not None:
            mod_args["new_party_size"] = context["current_party_size"]
            
        # Only proceed if at least one modification field is provided
        if len(mod_args) > 1:  # more than just the reservation_id
            result = modify_reservation(**mod_args)
            globals()["conversation_context"] = create_conversation_context()
            return result
        else:
            return "What would you like to change about your reservation? The date, time, or party size?"
    
    elif intent == "cancel_reservation" and context["current_reservation_id"] is not None:
        result = cancel_reservation(reservation_id=context["current_reservation_id"])
        globals()["conversation_context"] = create_conversation_context()
        return result
    
    elif intent == "get_reservation_details" and context["current_reservation_id"] is not None:
        result = get_reservation_details(reservation_id=context["current_reservation_id"])
        return result
    
    elif intent == "recommend_restaurant":
        # Build arguments with whatever information we have
        rec_args = {}
        if context["current_cuisine"] is not None:
            rec_args["cuisine"] = context["current_cuisine"]
        if context["current_party_size"] is not None:
            rec_args["party_size"] = context["current_party_size"]
            
        # Store the recommendations in the context
        result = recommend_restaurant(**rec_args)
        
        # If it's a successful recommendation (not an error message)
        if "Recommended Restaurants:" in result:
            # Don't reset context so we can use it for a subsequent reservation
            return result
        else:
            return result
    
    # If we reach here, we need to use the regular function calling mechanism
    # First, check if it's a general query that needs SQL generation
    if intent == "general_query":
        response = process_general_query(user_input)
        if response:
            return response
    
    # If not handled by context or as a general query, proceed with the existing LLM-based approach
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
    11. Don't ask for details all at once, ask for one detail at a time.
    
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
