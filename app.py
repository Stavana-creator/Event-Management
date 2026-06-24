print("================================")
print("RUNNING THIS APP.PY")
print("================================")
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import os
import webbrowser
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "eventsphere123"
app.config['UPLOAD_FOLDER'] = 'static/uploads'

print("Current directory:", os.getcwd())
print("Template folder:", app.template_folder)

print("\nFiles inside templates:")
print(os.listdir("templates"))

db = mysql.connector.connect(
    host="localhost",
    port=3307,
    user="root",
    password="Your_password",
    database="college_events"
)


@app.route("/")
def home():
    return render_template("index.html")
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(
         request.form["password"]
)

        cursor = db.cursor()   # <-- MUST be here

        query = """
        INSERT INTO students(name,email,password)
        VALUES(%s,%s,%s)
        """

        values = (name, email, password)

        try:
            cursor.execute(query, values)
            db.commit()
            flash("🎉 Registration Successful! Welcome to EventSphere.")
            return redirect(url_for("home"))

        
        except mysql.connector.IntegrityError:
            flash("❌ Email already registered. Please use another email.")
            return redirect(url_for("register"))

    return render_template("student_register.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor()

        query = """
        SELECT * FROM students
        WHERE email=%s
        """

        cursor.execute(query, (email,))

        student = cursor.fetchone()

        if student and check_password_hash(
                student[3],
                password
        ):

            session["student_id"] = student[0]

            return redirect(
                url_for("student_dashboard")
            )

        else:
            return "Invalid Email or Password"

    return render_template("student_login.html")
@app.route("/student_dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect(url_for("login"))

    return render_template("student_dashboard.html")
@app.route("/hello")
def hello():
    return "HELLO WORKING"
@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        query = """
        SELECT * FROM admins
        WHERE username=%s AND password=%s
        """

        cursor.execute(query, (username, password))

        admin = cursor.fetchone()

        if admin:
            cursor.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM students")
            total_students = cursor.fetchone()[0]
            session["admin"] = username
            return render_template("admin_dashboard.html",
        total_events=total_events,
        total_students=total_students
            )
    
        else:
            return "Invalid Admin Credentials"

    return render_template("admin_login.html")
from flask import redirect, url_for, flash
@app.route("/admin_dashboard")
def admin_dashboard():

    cursor = db.cursor()

    # Total Events
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    # Total Students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Total Registrations
    cursor.execute("SELECT COUNT(*) FROM registrations")
    total_registrations = cursor.fetchone()[0]

    # Upcoming Events
    cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE event_date >= CURDATE()
    """)
    upcoming_events = cursor.fetchone()[0]

    # Category Analytics
    cursor.execute("""
        SELECT category, COUNT(*)
        FROM events
        WHERE category IS NOT NULL
        GROUP BY category
    """)
    category_data = cursor.fetchall()

    print("CATEGORY DATA =", category_data)

    return render_template(
        "admin_dashboard.html",
        total_events=total_events,
        total_students=total_students,
        total_registrations=total_registrations,
        upcoming_events=upcoming_events,
        category_data=category_data
    )
@app.route("/add_event", methods=["GET", "POST"])
def add_event():

    if request.method == "POST":

        event_name = request.form["event_name"]
        event_date = request.form["event_date"]
        venue = request.form["venue"]
        description = request.form["description"]
        category = request.form["category"]
        status = request.form["status"]

        # Poster Upload
        poster = request.files["poster"]

        filename = None

        if poster and poster.filename != "":
            filename = secure_filename(poster.filename)

            upload_path = os.path.join(
                app.root_path,
                "static",
                "uploads",
                filename
            )

            poster.save(upload_path)

        cursor = db.cursor()

        query = """
        INSERT INTO events(
            event_name,
            event_date,
            venue,
            description,
            category,
            status,
            poster
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(
            query,
            (
                event_name,
                event_date,
                venue,
                description,
                category,
                status,
                filename
            )
        )

        db.commit()

        flash("✅ Event Added Successfully!")

        return redirect(url_for("admin_dashboard"))

    return render_template("add_event.html")
@app.route("/view_events")
def view_events():

    cursor = db.cursor()

    cursor.execute("SELECT * FROM events")

    events = cursor.fetchall()

    return render_template(
        "view_events.html",
        events=events
    )
@app.route("/register_event/<int:event_id>")
def register_event(event_id):

    student_id = session.get("student_id")

    if not student_id:
        flash("🔒 Please login first.")
        return redirect(url_for("login"))

    cursor = db.cursor()

    check_query = """
    SELECT * FROM registrations
    WHERE student_id=%s AND event_id=%s
    """

    cursor.execute(check_query, (student_id, event_id))
    existing = cursor.fetchone()

    if existing:
        flash("⚠️ You already registered for this event.")
        return redirect(url_for("view_events"))

    query = """
    INSERT INTO registrations(student_id, event_id)
    VALUES(%s, %s)
    """

    cursor.execute(query, (student_id, event_id))
    db.commit()

    flash("✅ Event Registered Successfully!")

    return redirect(url_for("view_events"))
@app.route("/my_events")
def my_events():

    student_id = session.get("student_id")

    if not student_id:
        flash("🔒 Please login as a student first.")
        return redirect(url_for("login"))

    cursor = db.cursor()

    query = """
    SELECT e.event_name, e.event_date, e.venue
    FROM events e
    JOIN registrations r
    ON e.event_id = r.event_id
    WHERE r.student_id = %s
    """

    cursor.execute(query, (student_id,))

    events = cursor.fetchall()

    print(events)

    return render_template(
        "my_events.html",
        events=events
    )
@app.route("/test")
def test():
    return "TEST ROUTE WORKING"

print(app.url_map)
@app.route("/manage_events")
def manage_events():

    search = request.args.get("search", "")

    cursor = db.cursor()

    query = """
    SELECT *
    FROM events
    WHERE event_name LIKE %s
    """

    cursor.execute(query, ('%' + search + '%',))

    events = cursor.fetchall()

    return render_template(
        "manage_events.html",
        events=events
    )
@app.route("/delete_event/<int:event_id>")
def delete_event(event_id):

    cursor = db.cursor()

    # Delete related registrations first
    cursor.execute(
        "DELETE FROM registrations WHERE event_id=%s",
        (event_id,)
    )

    # Then delete the event
    cursor.execute(
        "DELETE FROM events WHERE event_id=%s",
        (event_id,)
    )

    db.commit()

    flash("🗑️ Event Deleted Successfully!")
    return redirect(url_for("manage_events"))
@app.route("/edit_event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):

    cursor = db.cursor()

    if request.method == "POST":

        event_name = request.form["event_name"]
        event_date = request.form["event_date"]
        venue = request.form["venue"]
        description = request.form["description"]

        query = """
        UPDATE events
        SET event_name=%s,
            event_date=%s,
            venue=%s,
            description=%s
        WHERE event_id=%s
        """

        cursor.execute(
            query,
            (
                event_name,
                event_date,
                venue,
                description,
                event_id
            )
        )

        db.commit()

        flash("✏️ Event Updated Successfully!")
        return redirect(url_for("manage_events"))

    cursor.execute(
        "SELECT * FROM events WHERE event_id=%s",
        (event_id,)
    )

    event = cursor.fetchone()

    return render_template(
        "edit_event.html",
        event=event
    )
@app.route("/logout")
def logout():

    session.clear()

    flash("👋 Logged Out Successfully!") 
    return redirect(url_for("home"))
@app.route("/event_report")
def event_report():

    cursor = db.cursor()

    query = """
    SELECT
        e.event_name,
        e.event_date,
        e.venue,
        COUNT(r.registration_id) AS total_registrations
    FROM events e
    LEFT JOIN registrations r
    ON e.event_id = r.event_id
    GROUP BY e.event_id
    """

    cursor.execute(query)
    report = cursor.fetchall()
    cursor.execute("""
            SELECT
                   e.event_name,
    COUNT(r.registration_id) AS total
                   FROM events e
                   LEFT JOIN registrations r
                   ON e.event_id = r.event_id
                   GROUP BY e.event_id
                   ORDER BY total DESC
                   LIMIT 1
                   """)
    popular_event = cursor.fetchone()

    
    

    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM registrations")
    total_registrations = cursor.fetchone()[0]

    # ADD THESE TWO LINES
    labels = [row[0] for row in report]
    registrations = [row[3] for row in report]
    cursor.execute("""
             SELECT *
                FROM events
                ORDER BY event_date DESC
                LIMIT 5
                """)

    events = cursor.fetchall()

    return render_template(
        "event_report.html",
        report=report,
        total_events=total_events,
        total_students=total_students,
        total_registrations=total_registrations,
        labels=labels,
        registrations=registrations,
        popular_event=popular_event,
        events=events
    )
@app.route("/search_events", methods=["GET", "POST"])
def search_events():

    cursor = db.cursor()

    if request.method == "POST":

        keyword = request.form["keyword"]

        query = """
        SELECT * FROM events
        WHERE event_name LIKE %s
        """

        cursor.execute(query, ("%" + keyword + "%",))

        events = cursor.fetchall()

        return render_template(
            "search_events.html",
            events=events
        )

    return render_template(
        "search_events.html",
        events=[]
    )
@app.route("/cancel_registration/<int:event_id>")
def cancel_registration(event_id):

    student_id = session["student_id"]

    cursor = db.cursor()

    cursor.execute(
        """
        DELETE FROM registrations
        WHERE student_id=%s
        AND event_id=%s
        """,
        (student_id, event_id)
    )

    db.commit()

    flash("❌ Registration Cancelled!")
    return redirect(url_for("manage_events"))
print(app.url_map)
if __name__ == "__main__":

    threading.Timer(
        1,
        lambda: webbrowser.open(
            "http://127.0.0.1:5000"
        )
    ).start()

    app.run(debug=True, use_reloader=False)