import io
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import mysql.connector
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "taphealth_secret"

# ---------- OPENAI ----------
client = OpenAI(api_key="YOUR_OPENAI_API_KEY_HERE")

# ---------- DB CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Aditya",
        database="TapHealth"
    )

# ---------- DB FUNCTIONS ----------
def create_user(name, email, password):
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO users (user_name, user_email, user_password) VALUES (%s,%s,%s)",
        (name, email, password)
    )
    con.commit()
    cur.close()
    con.close()

def get_user(email):
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT user_id, user_name, user_password FROM users WHERE user_email=%s",
        (email,)
    )
    user = cur.fetchone()
    cur.close()
    con.close()
    return user

def get_user_files(user_id):
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT file_name, file_date FROM file WHERE user_id=%s",
        (user_id,)
    )
    files = cur.fetchall()
    cur.close()
    con.close()
    return files

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def loginpage():
    if request.method == "POST":
        email = request.form.get("user_email")
        password = request.form.get("user_password")

        user = get_user(email)
        if user and password == user[2]:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect(url_for("Dashboard"))

        flash("Invalid credentials", "error")
    return render_template("loginpage.html")

@app.route("/register", methods=["POST"])
def register():
    create_user(
        request.form.get("user_name"),
        request.form.get("user_email"),
        request.form.get("user_password")
    )
    flash("Account created!", "success")
    return redirect(url_for("loginpage"))

@app.route("/Dashboard")
def Dashboard():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    return render_template(
        "Dashboard.html",
        user_name=session["user_name"],
        files=get_user_files(session["user_id"])
    )

@app.route("/documents")
def documents():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    return render_template(
        "document.html",
        user_name=session["user_name"],
        files=get_user_files(session["user_id"])
    )

@app.route('/insurance')
def insurance():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    return render_template("insurance.html", user_name=session["user_name"])

# ---------- FILE UPLOAD (ONLY ONCE) ----------
@app.route("/document_upload", methods=["POST"])
def document_upload():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    file = request.files.get("file")
    if not file:
        flash("No file selected", "error")
        return redirect(url_for("documents"))

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO file (user_id, file_name, file_data, file_date)
        VALUES (%s,%s,%s,%s)
        """,
        (
            session["user_id"],
            file.filename,
            file.read(),
            date.today()
        )
    )
    con.commit()
    cur.close()
    con.close()

    flash("File uploaded successfully!", "success")
    return redirect(url_for("documents"))

# ---------- FILE DOWNLOAD ----------
@app.route("/download/<filename>")
def download_file(filename):
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT file_data FROM file WHERE user_id=%s AND file_name=%s",
        (session["user_id"], filename)
    )
    row = cur.fetchone()
    cur.close()
    con.close()

    if not row:
        flash("File not found", "error")
        return redirect(url_for("documents"))

    return send_file(
        io.BytesIO(row[0]),
        download_name=filename,
        as_attachment=True
    )

# ---------- EXTRA PAGES ----------
@app.route("/information")
def information():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    return render_template("information.html", user_name=session["user_name"])

@app.route("/Map")
def Map():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    return render_template("Map.html", user_name=session["user_name"])

@app.route("/emergency")
def emergency():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    return render_template("e.html", user_name=session["user_name"])

# ---------- WELLNESS ----------
@app.route("/Wellness")
def Wellness():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    return render_template("Wellness.html", user_name=session["user_name"])

# ---------- AI CHAT ----------
@app.route("/ai_chat", methods=["POST"])
def ai_chat():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    user_input = request.form.get("user_input")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly health assistant. Keep replies short and helpful."},
                {"role": "user", "content": user_input}
            ]
        )
        ai_response = response.choices[0].message.content
    except Exception as e:
        print(e)
        ai_response = "AI service unavailable right now."

    return render_template(
        "Wellness.html",
        user_name=session["user_name"],
        ai_response=ai_response
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
