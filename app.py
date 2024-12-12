from flask import Flask, render_template, request, redirect, flash, url_for, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import boto3
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)
app.secret_key = "your_secret_key"
s3_client = boto3.client('s3')

UPLOAD_FOLDER = r'static\images\uploads'  # Ensure this folder exists and is writable
MEDIA_FOLDER = r'static\videos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Define allowed file types

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['MEDIA_FOLDER'] = MEDIA_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# MySQL Configuration
db_config = {
    'host': 'eventmanagementdb.c1osgyis4swa.us-east-1.rds.amazonaws.com',
    'user': 'admin',
    'password': '2022510025Ramz',
    'database': 'EventHive'
}

# db_config = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': 'password',
#     'database': 'EventHive'
# }


def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        flash(f"Database connection error: {str(e)}", "danger")
        return None

# User Authentication Routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        email = request.form['email'].strip()
        name = request.form['name'].strip()
        phone_number = request.form['phone_number'].strip()

        if not username or not password or not email or not name or not phone_number:
            flash("All fields are required!", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        try:
            db = get_db_connection()
            if db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    INSERT INTO Users (username, password, email, name, phone_number)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (username, hashed_password, email, name, phone_number)
                )
                db.commit()
                user_id = cursor.lastrowid
                # Auto-login
                session['user_id'] = user_id
                flash("Account created successfully! You are now logged in.", "success")
                return redirect(url_for('home'))
        except Error as e:
            flash(f"Error while creating account: {str(e)}", "danger")
        finally:
            if db and db.is_connected():
                cursor.close()
                db.close()

    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            db = get_db_connection()
            if db:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT user_id, password FROM Users WHERE email = %s", (email,))
                user = cursor.fetchone()

        except Error as e:
            flash(f"Database error: {str(e)}", "danger")
            return redirect(url_for('signin'))
        finally:
            if db and db.is_connected():
                cursor.close()
                db.close()

        # Validate credentials
        if user is None:
            flash("Email not found. Please sign up.", "danger")
            return redirect(url_for('signup'))
        elif not check_password_hash(user['password'], password):
            flash("Incorrect password. Please try again.", "danger")
        else:
            session['user_id'] = user['user_id']  # Store user ID in session
            try:
                db = get_db_connection()
                if db:
                    cursor = db.cursor()
                    cursor.execute(
                        """
                        INSERT INTO UserSessions (user_id) 
                        VALUES (%s)
                        """,
                        (user['user_id'],)
                    )
                    db.commit()
            except Error as e:
                flash(f"Error logging session: {str(e)}", "danger")
            finally:
                if db and db.is_connected():
                    cursor.close()
                    db.close()

            flash("Welcome back!", "success")
            return redirect(url_for('home'))

    return render_template('signin.html')

@app.route('/signout', methods=['POST'])
def signout():
    user_id = session.get('user_id')
    if user_id:
        try:
            db = get_db_connection()
            if db:
                cursor = db.cursor()
                cursor.execute(
                    """
                    UPDATE UserSessions
                    SET logged_out_at = NOW(), is_active = FALSE
                    WHERE user_id = %s AND is_active = TRUE
                    """,
                    (user_id,)
                )
                db.commit()
        except Error as e:
            flash(f"Error updating session: {str(e)}", "danger")
        finally:
            if db and db.is_connected():
                cursor.close()
                db.close()
        
        # Remove user from session
        session.pop('user_id', None)
        flash("You have been signed out.", "info")

    return redirect(url_for('home'))

# Event Management Functions
def get_events(event_type='', location='', start_date='', end_date=''):
    events = []
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            current_datetime = datetime.now()
            query = """
                SELECT event_id, title, event_type, description, start_date, end_date, 
                       start_time, end_time, street, city, state, country, views, tags, image_path
                FROM Events 
                WHERE (start_date > %s OR (start_date = %s AND start_time >= %s))
            """
            params = [current_datetime.date(), current_datetime.date(), current_datetime.time()]

            if event_type and event_type != "All":
                query += " AND event_type = %s"
                params.append(event_type)

            if location:
                query += " AND (city LIKE %s OR state LIKE %s OR country LIKE %s)"
                location_pattern = f"%{location}%"
                params.extend([location_pattern] * 3)

            if start_date:
                query += " AND start_date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND end_date <= %s"
                params.append(end_date)

            query += " ORDER BY start_date, start_time ASC"
            cursor.execute(query, tuple(params))
            events = cursor.fetchall()
            
    except Error as e:
        flash(f"Error fetching events: {str(e)}", "danger")
        events = []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return events

def get_event_details(event_id):
    event = []
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT title, event_type, description, start_date, end_date, start_time, end_time, 
                       street, city, state, country, views, tags, created_by, image_path
                FROM Events 
                WHERE event_id = %s
            """
            cursor.execute(query, (event_id,))
            event = cursor.fetchone()
    except Error as e:
        flash(f"Error fetching event details: {str(e)}", "danger")
        event = None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return event

def get_unique_event_types():
    event_types = []
    today = datetime.today().strftime('%Y-%m-%d')
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT event_type 
                FROM Events 
                WHERE start_date >= %s
            """, (today,))
            event_types = cursor.fetchall()
    except Error as e:
        flash(f"Error fetching event types: {str(e)}", "danger")
        event_types = []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return event_types

def upload_to_s3(file, bucket_name, file_name):
    try:
        s3_client.upload_fileobj(
            file,
            bucket_name,
            file_name,
        )
        return f"https://{bucket_name}.s3.us-east-1.amazonaws.com/{file_name}"
    except NoCredentialsError:
        return "Credentials not available"

@app.route('/', methods=['GET', 'POST'])
def home():
    # Get filters from the request
    event_type = request.args.get('event_type', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search_query = request.args.get('search_query', '')

    current_date = datetime.now().date()

    # Fetch the filtered events
    events = get_events(event_type, location, start_date, end_date)
    event_types = get_unique_event_types()

    user_events = {}  # Change to a dictionary
    if 'user_id' in session:
        try:
            db = get_db_connection()
            if db:
                cursor = db.cursor()

                # Query to get events the user has registered for
                cursor.execute("""
                    SELECT b.event_id, e.title, e.views, e.start_date, e.end_date, e.image_path
                    FROM Bookings b
                    JOIN Events e ON b.event_id = e.event_id
                    WHERE b.user_id = %s
                """, (session['user_id'],))

                # Fetch all the user's registered events
                registered_events = cursor.fetchall()

                # For each event, fetch the total tickets sold
                for event in registered_events:
                    event_id = event[0]
                    cursor.execute("""
                        SELECT SUM(total_tickets_sold) FROM Pricing_Tiers
                        WHERE event_id = %s
                    """, (event_id,))
                    total_tickets_sold = cursor.fetchone()[0] or 0
                    user_events[event_id] = {
                        'title': event[1],
                        'views': event[2],
                        'start_date': event[3],
                        'end_date': event[4],
                        'total_tickets_sold': int(total_tickets_sold),
                        'status': 'Registered',
                        'image_path': event[5]
                    }

                # Query to get events the user has created
                cursor.execute("""
                    SELECT e.event_id, e.title, e.views, e.start_date, e.end_date, e.image_path
                    FROM Events e
                    WHERE e.created_by = %s
                """, (session['user_id'],))

                # Fetch all the user's created events
                created_events = cursor.fetchall()

                # For each created event, fetch the total tickets sold
                for event in created_events:
                    event_id = event[0]
                    cursor.execute("""
                        SELECT SUM(total_tickets_sold) FROM Pricing_Tiers
                        WHERE event_id = %s
                    """, (event_id,))
                    total_tickets_sold = cursor.fetchone()[0] or 0
                    user_events[event_id] = {
                        'title': event[1],
                        'views': event[2],
                        'start_date': event[3],
                        'end_date': event[4],
                        'total_tickets_sold': int(total_tickets_sold),
                        'status': 'Created',  # Event type
                        'image_path' : event[5]
                    }

        except Error as e:
            flash(f"Error fetching user events: {str(e)}", "danger")
        finally:
            if db and db.is_connected():
                cursor.close()
                db.close()

    # Render the homepage with filtered events and user-registered/created events
    return render_template(
        'HomePage.html', 
        events=events, 
        event_types=event_types,
        event_type=event_type, 
        location=location, 
        start_date=start_date, 
        end_date=end_date, 
        search_query=search_query,
        user_events=user_events,  # Pass the user events as a dictionary
        current_date=current_date  # Pass the current date to the template
    )

@app.route('/<int:event_id>')
def event_page(event_id):
    # Fetch event details
    event = get_event_details(event_id)

    if not event:
        return "Event not found", 404

    # Determine if the logged-in user is the event creator
    display_admin_panel = False
    if 'user_id' in session and session['user_id'] == event['created_by']:
        display_admin_panel = True

    # Initialize variables
    total_views = None
    tier_data = []
    total_tickets_sold = 0
    total_available_tickets = 0
    event_media = None

    try:
        # Connect to the database
        db = get_db_connection()
        if db:
            cursor = db.cursor()

            # Increment the views count
            cursor.execute("""
                UPDATE Events
                SET views = views + 1
                WHERE event_id = %s
            """, (event_id,))
            db.commit()

            # Fetch the total views
            cursor.execute("SELECT views FROM Events WHERE event_id = %s", (event_id,))
            total_views = cursor.fetchone()[0]

            # Fetch media URL for the event
            cursor.execute("SELECT media_url FROM Event_Media WHERE event_id = %s", (event_id,))
            media_result = cursor.fetchone()
            event_media = media_result[0] if media_result else None

            # If the user is the event creator, fetch dashboard details
            if display_admin_panel:
                # Fetch tier details
                cursor.execute("""
                    SELECT tier_name, available_tickets, total_tickets_sold
                    FROM Pricing_Tiers
                    WHERE event_id = %s
                """, (event_id,))
                tier_data = cursor.fetchall()

                # Calculate total tickets sold and available tickets
                for tier in tier_data:
                    total_tickets_sold += tier[2]  # Sum of total_tickets_sold
                    total_available_tickets += tier[1]  # Sum of available_tickets

    except mysql.connector.Error as e:
        flash(f"Database error: {str(e)}", "danger")
    finally:
        # Close cursor and connection
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    # Log information for debugging
    print(f"Event Media: {event_media}")
    print(f"Total Views: {total_views}")
    print(f"Tier Data: {tier_data}")
    print(f"Total Tickets Sold: {total_tickets_sold}, Total Available Tickets: {total_available_tickets}")

    # Render the template with fetched data
    return render_template(
        'EventPage.html',
        event=event,
        total_views=total_views,
        tier_data=tier_data,
        total_tickets_sold=total_tickets_sold,
        total_available_tickets=total_available_tickets,
        display_admin_panel=display_admin_panel,
        event_id=event_id,
        event_media=event_media
    )

# Success Page
@app.route('/success')
def success():
    return render_template('success.html', message="Welcome!")

@app.route('/createevent', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        # Capture form data
        title = request.form['event-title']
        event_type = request.form['event-type']
        description = request.form['event-description']
        start_date = request.form['event-start-date']
        end_date = request.form['event-end-date']
        start_time = request.form['event-start-time']
        end_time = request.form['event-end-time']
        street = request.form['event-venue']
        city = request.form['event-city']
        state = request.form['event-state']
        country = request.form['event-country']
        tags = request.form['event-tags']
        user_id = session.get('user_id')

        # Capture pricing tiers
        tier_names = request.form.getlist('tier-name[]')
        tier_prices = request.form.getlist('tier-price[]')
        tier_quantities = request.form.getlist('tickets-max-count[]')
        tier_descriptions = request.form.getlist('tier-description[]')

        # Capture the uploaded image
        event_image = request.files.get('event-image')
        event_media = request.files.get('event-media')

        s3_img_url = ""
        s3_media_url = ""

        if event_image:
            # Upload the file to S3
            file_name = f"{title}_{event_image.filename}"
            s3_img_url = upload_to_s3(event_image, "eventmanagers3", f"images/{file_name}")

        if event_media:
            # Upload the file to S3
            file_name = f"{title}_{event_media.filename}"
            s3_media_url = upload_to_s3(event_media, "eventmanagers3", f"media/{file_name}")

        if event_image and allowed_file(event_image.filename):
            try:
                # Database connection
                db = get_db_connection()
                cursor = db.cursor()
                view_ct = 0
                # Insert event data into the database
                cursor.execute("""
                    INSERT INTO Events (title, event_type, description, start_date, end_date, start_time, end_time, street, city, state, country, views, tags, created_by, image_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (title, event_type, description, start_date, end_date, start_time, end_time, street, city, state, country, view_ct, tags, user_id, s3_img_url))

                # Get the newly inserted event ID
                event_id = cursor.lastrowid

                # Save pricing tiers
                for i in range(len(tier_names)):
                    cursor.execute("""
                        INSERT INTO Pricing_Tiers (event_id, tier_name, tier_description, price, available_tickets)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (event_id, tier_names[i], tier_descriptions[i], tier_prices[i], tier_quantities[i]))

                if s3_media_url:
                    # Insert media URL into Event_Media table
                    cursor.execute("""
                        INSERT INTO Event_Media (event_id, media_url, sequence)
                        VALUES (%s, %s, 1)
                    """, (event_id, s3_media_url))

                # Commit the transaction
                db.commit()
                flash("Event created successfully!", "success")
                return redirect(url_for('home'))

            except Exception as e:
                db.rollback()
                print(f"Error: {e}")
                flash(f"Error creating event: {str(e)}", "danger")
            finally:
                if db.is_connected():
                    cursor.close()
                    db.close()

        else:
            flash("Invalid file type or no file uploaded!", "danger")

    return render_template('CreateEventPage.html')


@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch event details
    cursor.execute("SELECT * FROM Events WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()

    # Fetch pricing tiers for the event
    cursor.execute("SELECT * FROM Pricing_Tiers WHERE event_id = %s", (event_id,))
    tiers = cursor.fetchall()

    cursor.close()
    db.close()

    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for('home'))

    return render_template('RegistrationPage.html', event=event, tiers=tiers)

@app.route('/confirm_registration/<int:event_id>', methods=['POST'])
def confirm_registration(event_id):
    if 'user_id' not in session:
        flash("Please log in to book tickets.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    print(f"User ID: {user_id}")
    print(f"Event ID: {event_id}")

    # Extract and filter ticket counts
    ticket_counts = {key: int(value) for key, value in request.form.items() if value.isdigit()}
    print(f"Ticket Counts: {ticket_counts}")

    total_price = 0.0
    booking_details = []

    try:
        db = get_db_connection()
        cursor = db.cursor()
        print("Database connection established.")

        for tier_id, quantity in ticket_counts.items():
            print(f"Processing Tier ID: {tier_id}, Quantity: {quantity}")

            # Fetch tier details
            cursor.execute("""
                SELECT price, total_tickets_sold, available_tickets 
                FROM Pricing_Tiers 
                WHERE tier_id = %s
            """, (tier_id,))
            tier = cursor.fetchone()
            print(f"Tier Details: {tier}")

            if not tier:
                flash(f"Tier ID {tier_id} not found.", "danger")
                return redirect(url_for('register', event_id=event_id))

            price_per_ticket = float(tier[0])
            total_tickets_sold = int(tier[1])
            available_tickets = int(tier[2])
            print(f"Price per Ticket: {price_per_ticket}, Total Tickets Sold: {total_tickets_sold}, Available Tickets: {available_tickets}")

            # Check availability
            if total_tickets_sold + quantity > available_tickets:
                flash(f"Not enough tickets available for Tier ID {tier_id}.", "danger")
                return redirect(url_for('register', event_id=event_id))

            # Update total price and collect booking details
            total_price += price_per_ticket * quantity
            print(f"Updated Total Price: {total_price}")
            booking_details.append((tier_id, quantity, price_per_ticket))

        # Insert into Bookings table
        print(f"Inserting Booking: User ID: {user_id}, Event ID: {event_id}, Total Price: {total_price}")
        cursor.execute("""
            INSERT INTO Bookings (user_id, event_id, total_price) 
            VALUES (%s, %s, %s)
        """, (user_id, event_id, total_price))
        booking_id = cursor.lastrowid
        print(f"Booking ID: {booking_id}")

        # Insert into Booking_Details table and update tickets sold
        for tier_id, quantity, price_per_ticket in booking_details:
            print(f"Inserting Booking Details: Booking ID: {booking_id}, Tier ID: {tier_id}, Quantity: {quantity}, Price per Ticket: {price_per_ticket}")
            cursor.execute("""
                INSERT INTO Booking_Details (booking_id, tier_id, quantity, price_per_ticket) 
                VALUES (%s, %s, %s, %s)
            """, (booking_id, tier_id, quantity, price_per_ticket))

            # Update total_tickets_sold
            print(f"Updating Total Tickets Sold: Tier ID: {tier_id}, Quantity: {quantity}")
            cursor.execute("""
                UPDATE Pricing_Tiers 
                SET total_tickets_sold = total_tickets_sold + %s 
                WHERE tier_id = %s
            """, (quantity, tier_id))

        # Commit transaction
        db.commit()
        print("Transaction committed successfully.")
        flash("Booking successful!", "success")
        return redirect(url_for('home'))

    except Exception as e:
        db.rollback()
        print(f"Error occurred: {e}")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('register', event_id=event_id))

    finally:
        if db.is_connected():
            print("Closing database connection.")
            cursor.close()
            db.close()








if __name__ == '__main__':
    app.run(debug=True)
