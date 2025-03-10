# Import required modules
from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt  # Password Hashing

# Initialize Flask app
app = Flask(__name__)

# Configure file uploads
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Secret key for authentication
app.config["SECRET_KEY"] = "your-secret-key"

# Configure Email Notifications (Optional)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "your-email@gmail.com"
app.config["MAIL_PASSWORD"] = "your-email-password"

mail = Mail(app)
bcrypt = Bcrypt(app)  # Initialize Flask-Bcrypt for password hashing

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "vip_login"  # Redirects unauthorized users to login page

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Database setup
def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            vip_level TEXT,
            gift_card_code TEXT,
            image_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            gift_card_code TEXT,
            image_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vip_members (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

create_database()

# Function to check allowed file uploads
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Save data to the database
def save_to_database(table, name, email, gift_card_code, image_path):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if table == "members":
        cursor.execute("INSERT INTO members (name, email, gift_card_code, image_path) VALUES (?, ?, ?, ?)", 
                       (name, email, gift_card_code, image_path))
    elif table == "donations":
        cursor.execute("INSERT INTO donations (name, email, gift_card_code, image_path) VALUES (?, ?, ?, ?)", 
                       (name, email, gift_card_code, image_path))

    conn.commit()
    conn.close()

# Home Page Route
@app.route("/")
def home():
    return render_template("index.html")

# VIP Membership Registration Route
@app.route("/vip<int:vip_level>", methods=["GET", "POST"])
def vip_registration(vip_level):
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        gift_card_code = request.form["gift_card_code"]
        file = request.files["gift_card_image"]

        if file and allowed_file(file.filename):
            filename = f"VIP{vip_level}_{name.replace(' ', '_')}.jpg"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            save_to_database("members", name, email, gift_card_code, file_path)

            # Send Confirmation Email (Optional)
            try:
                msg = Message(f"VIP {vip_level} Membership Confirmation",
                              sender="your-email@gmail.com",
                              recipients=[email])
                msg.body = f"Hello {name},\n\nYour VIP {vip_level} registration is received. We will review your submission soon."
                mail.send(msg)
            except Exception as e:
                print("Email failed:", e)

            return f"VIP {vip_level} Registration Successful! Your submission is under review."
    return render_template("vip.html", vip_level=vip_level)

# Orphanage Donation Route
@app.route("/donate", methods=["GET", "POST"])
def donate():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        gift_card_code = request.form["gift_card_code"]
        file = request.files["gift_card_image"]

        if file and allowed_file(file.filename):
            filename = f"Donation_{name.replace(' ', '_')}.jpg"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            save_to_database("donations", name, email, gift_card_code, file_path)

            return "Thank you for your donation! Your submission is under review."
    return render_template("donate.html")

# Admin Panel to View VIP Registrations & Donations
@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    cursor.execute("SELECT * FROM donations")
    donations = cursor.fetchall()
    conn.close()
    return render_template("admin.html", members=members, donations=donations)

# User Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        if username == "admin" and password == "admin123":
            user = User(1)
            login_user(user)
            return redirect(url_for("admin"))
        else:
            return "Invalid credentials. Try again."

    return render_template("login.html")

# VIP Member Logout Route (Corrected)
@app.route("/vip_logout")
@login_required
def vip_logout():
    logout_user()
    return redirect(url_for("vip_login"))  # Redirects to correct VIP login page

# VIP Member Registration (Admin Only)
@app.route("/vip_register", methods=["GET", "POST"])
@login_required
def vip_register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO vip_members (email, password) VALUES (?, ?)", (email, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Email already registered as VIP."
        finally:
            conn.close()

        return "VIP Member Registered Successfully!"

    return render_template("vip_register.html")

# VIP Dashboard Route (Protected)
@app.route("/vip_dashboard")
@login_required
def vip_dashboard():
    return render_template("vip_dashboard.html", email=current_user.id)

# VIP Login Route
@app.route("/vip_login", methods=["GET", "POST"])
def vip_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM vip_members WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row and bcrypt.check_password_hash(row[0], password):
            user = User(email)
            login_user(user)
            return redirect(url_for("vip_dashboard"))
        else:
            return "Invalid email or password."

    return render_template("vip_login.html")

# Run the Flask App
if __name__ == "__main__":
    app.run(debug=True)
# Import required modules
from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt  # Password Hashing

# Initialize Flask app
app = Flask(__name__)

# Configure file uploads
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Secret key for authentication
app.config["SECRET_KEY"] = "your-secret-key"

# Configure Email Notifications (Optional)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "your-email@gmail.com"
app.config["MAIL_PASSWORD"] = "your-email-password"

mail = Mail(app)
bcrypt = Bcrypt(app)  # Initialize Flask-Bcrypt for password hashing

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "vip_login"  # Redirects unauthorized users to login page

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Database setup
def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            vip_level TEXT,
            gift_card_code TEXT,
            image_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            gift_card_code TEXT,
            image_path TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vip_members (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

create_database()

# Function to check allowed file uploads
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Save data to the database
def save_to_database(table, name, email, gift_card_code, image_path):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if table == "members":
        cursor.execute("INSERT INTO members (name, email, gift_card_code, image_path) VALUES (?, ?, ?, ?)", 
                       (name, email, gift_card_code, image_path))
    elif table == "donations":
        cursor.execute("INSERT INTO donations (name, email, gift_card_code, image_path) VALUES (?, ?, ?, ?)", 
                       (name, email, gift_card_code, image_path))

    conn.commit()
    conn.close()

# Home Page Route
@app.route("/")
def home():
    return render_template("index.html")

# VIP Membership Registration Route
@app.route("/vip<int:vip_level>", methods=["GET", "POST"])
def vip_registration(vip_level):
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        gift_card_code = request.form["gift_card_code"]
        file = request.files["gift_card_image"]

        if file and allowed_file(file.filename):
            filename = f"VIP{vip_level}_{name.replace(' ', '_')}.jpg"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            save_to_database("members", name, email, gift_card_code, file_path)

            # Send Confirmation Email (Optional)
            try:
                msg = Message(f"VIP {vip_level} Membership Confirmation",
                              sender="your-email@gmail.com",
                              recipients=[email])
                msg.body = f"Hello {name},\n\nYour VIP {vip_level} registration is received. We will review your submission soon."
                mail.send(msg)
            except Exception as e:
                print("Email failed:", e)

            return f"VIP {vip_level} Registration Successful! Your submission is under review."
    return render_template("vip.html", vip_level=vip_level)

# Orphanage Donation Route
@app.route("/donate", methods=["GET", "POST"])
def donate():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        gift_card_code = request.form["gift_card_code"]
        file = request.files["gift_card_image"]

        if file and allowed_file(file.filename):
            filename = f"Donation_{name.replace(' ', '_')}.jpg"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            save_to_database("donations", name, email, gift_card_code, file_path)

            return "Thank you for your donation! Your submission is under review."
    return render_template("donate.html")

# Admin Panel to View VIP Registrations & Donations
@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    cursor.execute("SELECT * FROM donations")
    donations = cursor.fetchall()
    conn.close()
    return render_template("admin.html", members=members, donations=donations)

# User Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        if username == "admin" and password == "admin123":
            user = User(1)
            login_user(user)
            return redirect(url_for("admin"))
        else:
            return "Invalid credentials. Try again."

    return render_template("login.html")

# VIP Member Logout Route (Corrected)
@app.route("/vip_logout")
@login_required
def vip_logout():
    logout_user()
    return redirect(url_for("vip_login"))  # Redirects to correct VIP login page

# VIP Member Registration (Admin Only)
@app.route("/vip_register", methods=["GET", "POST"])
@login_required
def vip_register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO vip_members (email, password) VALUES (?, ?)", (email, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Email already registered as VIP."
        finally:
            conn.close()

        return "VIP Member Registered Successfully!"

    return render_template("vip_register.html")

# VIP Dashboard Route (Protected)
@app.route("/vip_dashboard")
@login_required
def vip_dashboard():
    return render_template("vip_dashboard.html", email=current_user.id)

# VIP Login Route
@app.route("/vip_login", methods=["GET", "POST"])
def vip_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM vip_members WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row and bcrypt.check_password_hash(row[0], password):
            user = User(email)
            login_user(user)
            return redirect(url_for("vip_dashboard"))
        else:
            return "Invalid email or password."

    return render_template("vip_login.html")

# Run the Flask App
if __name__ == "__main__":
    from waitress import server 
    serve(app, host="0.0.0.0",
    port=8080)
    from flask import Flask, send_from_directory

app = Flask(__name__)

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)
