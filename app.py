from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from pymysql import MySQLError
import uuid
from flask import render_template, session
import boto3

app = Flask(__name__)
app.secret_key = "your_secret_key"  # For flash messages

# RDS configuration
rds_host = 'database-2.c3qeysk6ww3b.ap-south-1.rds.amazonaws.com'  # Replace with your RDS endpoint
rds_port = 3306  # Default MySQL port
db_username = 'admin'  # Replace with your database username
db_password = 'pranamidas1994'  # Replace with your database password
db_name = 'service'  # Replace with your database name

# Connect to the RDS MySQL database
def connect_to_rds():
    try:
        connection = pymysql.connect(
            host=rds_host,
            user=db_username,
            password=db_password,
            database=db_name,
            port=rds_port
        )
        print("Connected to the database!")
        return connection
    except MySQLError as e:
        print(f"Error connecting to the database: {e}")
        return None

def generate_unique_id():
    unique_id = uuid.uuid4()  # Generate a random UUID
    return f"ID{unique_id.hex[:10].upper()}"

@app.route('/')
def index():
    print("Entered the index route")
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    print("Entered the register route")
    if request.method == 'POST':
        name = request.form['name']
        phone_no = request.form['phone_no']
        address = request.form['address']
        email = request.form['email']
        password = request.form['password']

        connection = connect_to_rds()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute("""INSERT INTO user (name, address, phone_no, email, password) 
                               VALUES (%s, %s, %s, %s, %s)""",
                               (name, address, phone_no, email, password))
                connection.commit()
                print("Thanks for registering!", "success")
                return redirect(url_for('login'))
            except MySQLError as err:
                print(f"Error: {err}", "danger")
            finally:
                cursor.close()
                connection.close()
        else:
            print("Error connecting to the database")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Entered the login route")
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        connection = connect_to_rds()

        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT * FROM user WHERE email=%s AND password=%s", (email, password))
                user = cursor.fetchone()

                if user:
                    print("Current user:", user)
                    session['user_id'] = user[0]
                    session['name'] = user[1]
                    session['address'] = user[2]
                    session['phone_no'] = user[3]
                    session['email'] = user[4]

                    print("Login successful!", "success")
                    return redirect(url_for('select_service'))
                else:
                    print("Invalid login. Please try again.", "danger")
            except MySQLError as err:
                print(f"Error: {err}", "danger")
            finally:
                cursor.close()
                connection.close()
        else:
            print("Database connection failed!", "danger")

    return render_template('login.html')

@app.route('/select_service', methods=['GET', 'POST'])
def select_service():
    print("Entered the select_service route")
    connection = connect_to_rds()

    if request.method == 'POST':
        print("post")
        session['service'] = request.form['service']
        session['date'] = request.form['date']
        print(session['service'])
        if connection:
            cursor = connection.cursor()
            try:
                session['booking_id'] = generate_unique_id() 
                print(session['booking_id'])
                cursor.execute("""INSERT INTO booking_details(user_id, user_name, address, phone_no, booking_id, service, date,email)
                               VALUES (%s, %s, %s, %s, %s, %s, %s,%s)""",
                               (session['user_id'], session['name'], session['address'],
                                session['phone_no'], session['booking_id'], session['service'], session['date'],session['email']))
                connection.commit()

                return redirect(url_for('confirm_payment'))  # Corrected endpoint
            except MySQLError as err:
                print(f"Error: {err}", "danger")
            finally:
                cursor.close()
                connection.close()
        else:
            print("Error connecting to the database")
            return redirect(url_for('login'))

    return render_template('select_service.html')

@app.route('/select_payment_mode', methods=['GET', 'POST'])
def confirm_payment():
    print("Entered the confirm_payment route")
    if request.method == 'POST':
        # Handle payment confirmation process here
        return redirect(url_for('thankyou'))
    return render_template('select_payment_mode.html')



# @app.route('/thankyou')
# def thankyou():

#     connection = connect_to_rds()
#     if connection:

#         cursor = connection.cursor()
#         cursor.execute("select  * from booking_details where booking_id = %s",  (session['booking_id'],))
#         booking_details= cursor.fetchone()

#         keys=['user_id','user_name','address','phone_no','booking_id','service','date']
#         booking_details = dict(zip(keys, booking_details)) 

#         cursor.close()
        

#         return render_template('thankyou.html',booking_details = booking_details)



@app.route('/thankyou')
def thankyou():
    connection = connect_to_rds()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM booking_details WHERE booking_id = %s", (session['booking_id'],))
        booking_details = cursor.fetchone()
        cursor.close()

        keys = ['user_id', 'user_name','email', 'address', 'phone_no', 'booking_id', 'service', 'date']
        booking_details = dict(zip(keys, booking_details)) 

        # Send thank you email through SES
        send_thank_you_email_ses(session['email'], booking_details)

        return render_template('thankyou.html', booking_details=booking_details)

def send_thank_you_email_ses(email, booking_details):
    ses_client = boto3.client('ses', region_name='us-east-1')  # Replace with your SES region
    try:
        response = ses_client.send_email(
            Source='pranamidasts@gmail.com',  # Replace with your verified SES email
            Destination={
                'ToAddresses': [email]
            },
            Message={
                'Subject': {
                    'Data': 'Service Booking Confirmation'
                },
                'Body': {
                    'Text': {
                        'Data': (
                            f"Dear {booking_details['user_name']},\n\n"
                            f"Your booking for {booking_details['service']} on {booking_details['date']} "
                            f"has been confirmed with ID: {booking_details['booking_id']}.\n\n"
                            "Thank you for choosing our services!"
                        )
                    }
                }
            }
        )
        print("Email sent! Message ID:", response['MessageId'])
    except Exception as e:
        print(f"Error sending email: {e}")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
