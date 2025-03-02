import psycopg2
import streamlit as st
from datetime import datetime
import random

def get_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            database=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            port=st.secrets["DB_PORT"]
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def recommend_restaurant(cuisine=None, party_size=None, rating=None, address=None):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        query = "SELECT name, cuisine, rating, address FROM restaurants WHERE 1=1"
        params = []

        if cuisine:
            query += " AND cuisine ILIKE %s"
            params.append(f"%{cuisine}%")
        if party_size:
            query += " AND seating_capacity >= %s"
            params.append(party_size)
        if rating:
            query += " AND rating >= %s"
            params.append(rating)
        if address:
            query += " AND address ILIKE %s"
            params.append(f"%{address}%")

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        if results:
            recommendations = "\n".join([f"- **{name}**: {cuisine}, Rating: {rating}, Address: {address}" for name, cuisine, rating, address in results])
            return f"Recommended Restaurants:\n{recommendations}"
        else:
            return "No restaurants match your criteria."
    except psycopg2.Error as e:
        conn.close()
        return f"Database error during recommendation: {e}"

def make_reservation(restaurant_name, date, time, party_size, customer_name):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, seating_capacity, current_booking FROM restaurants WHERE name = %s", (restaurant_name,))
        restaurant = cursor.fetchone()

        if not restaurant:
            conn.close()
            return f"Restaurant '{restaurant_name}' not found."

        restaurant_id, capacity, current_booking = restaurant

        if current_booking + party_size > capacity:
            conn.close()
            return f"Sorry, there are not enough spots available at {restaurant_name} on {date} at {time}. Would you like to check other options?"

        # Convert date to YYYY-MM-DD format
        try:
            date_obj = datetime.strptime(date, "%d-%m-%Y").date()
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            conn.close()
            return "Invalid date format. Please use DD-MM-YYYY."

        # Generate random reservation_id
        reservation_id = random.randint(100000, 999999)  # Generate a 6-digit random ID

        cursor.execute(
            "INSERT INTO reservations (reservation_id, restaurant_id, customer_name, date, time, party_size) VALUES (%s, %s, %s, %s, %s, %s)",
            (reservation_id, restaurant_id, customer_name, formatted_date, time, party_size),
        )

        cursor.execute("UPDATE restaurants SET current_booking = current_booking + %s WHERE id = %s", (party_size, restaurant_id))

        conn.commit()
        conn.close()

        return f"Reservation confirmed for {customer_name} at {restaurant_name} on {date} at {time} for {party_size} people. Reservation ID: {reservation_id}"
    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        return f"Database error during reservation: {e}"

def modify_reservation(customer_name, date, time, new_date=None, new_time=None, new_party_size=None):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT reservation_id, restaurant_id, party_size FROM reservations WHERE customer_name = %s AND date = %s AND time = %s", (customer_name, date, time))
        reservation = cursor.fetchone()

        if not reservation:
            conn.close()
            return "Reservation not found."

        reservation_id, restaurant_id, current_party_size = reservation

        if new_party_size:
            cursor.execute("SELECT seating_capacity, current_booking FROM restaurants WHERE id = %s", (restaurant_id,))
            capacity, current_booking_restaurant = cursor.fetchone()

            cursor.execute("SELECT SUM(party_size) FROM reservations WHERE restaurant_id = %s AND date = %s AND time = %s AND reservation_id != %s", (restaurant_id, new_date or date, new_time or time, reservation_id))
            total_reserved = cursor.fetchone()[0] or 0

            if current_booking_restaurant - current_party_size + new_party_size > capacity:
                conn.close()
                return "The restaurant does not have enough capacity for the new party size."

        # Convert new_date to YYYY-MM-DD format if provided
        if new_date:
            try:
                date_obj = datetime.strptime(new_date, "%d-%m-%Y").date()
                formatted_new_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                conn.close()
                return "Invalid new date format. Please use DD-MM-YYYY."
        else:
            formatted_new_date = None

        cursor.execute(
            "UPDATE reservations SET date = %s, time = %s, party_size = %s WHERE reservation_id = %s",
            (formatted_new_date or date, new_time or time, new_party_size or current_party_size, reservation_id),
        )

        if new_party_size:
            cursor.execute("UPDATE restaurants SET current_booking = current_booking - %s + %s WHERE id = %s", (current_party_size, new_party_size, restaurant_id))

        conn.commit()
        conn.close()

        return f"Reservation modified successfully. Reservation ID: {reservation_id}"
    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        return f"Database error during modification: {e}"

def cancel_reservation(customer_name, date, time):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT reservation_id, restaurant_id, party_size FROM reservations WHERE customer_name = %s AND date = %s AND time = %s", (customer_name, date, time))
        reservation = cursor.fetchone()

        if not reservation:
            conn.close()
            return "Reservation not found."

        reservation_id, restaurant_id, party_size = reservation

        cursor.execute("DELETE FROM reservations WHERE customer_name = %s AND date = %s AND time = %s", (customer_name, date, time))

        cursor.execute("UPDATE restaurants SET current_booking = current_booking - %s WHERE id = %s", (party_size, restaurant_id))

        conn.commit()
        conn.close()
        return f"Reservation canceled successfully. Reservation ID: {reservation_id}"
    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        return f"Database error during cancellation: {e}"
    

def get_reservation_details(reservation_id):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT r.reservation_id, rest.name,r.customer_name, r.date, r.time, r.party_size
            FROM reservations r
            JOIN restaurants rest ON r.restaurant_id = rest.id
            WHERE r.reservation_id = %s
        """, (reservation_id,))
        reservation = cursor.fetchone()

        conn.close()

        if reservation:
            reservation_id, restaurant_name, customer_name, date, time, party_size = reservation
            return f"Reservation ID: {reservation_id}\nRestaurant: {restaurant_name}\nCustomer: {customer_name}\nDate: {date}\nTime: {time}\nParty Size: {party_size}"
        else:
            return "Reservation not found."
    except psycopg2.Error as e:
        conn.close()
        return f"Database error during reservation details retrieval: {e}"

def execute_sql_query(query):
    conn = get_connection()
    if conn is None:
        return "Database connection failed. Please check your credentials."
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        
        # Check if this is a SELECT query that returns results
        if cursor.description is not None:
            results = cursor.fetchall()
            conn.close()
            return results
        else:
            # This was a non-SELECT query
            conn.rollback()  # Roll back any changes
            conn.close()
            return "This query does not return any results or is not allowed."
    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        return f"Database error: {e}"
