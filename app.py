from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from textblob import TextBlob
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "campus_secret"

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect("feedback.db")
    conn.row_factory = sqlite3.Row # Allows accessing data by column name
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                student TEXT,
                rating INTEGER,
                comment TEXT,
                sentiment TEXT
            )
        """)
        conn.commit()

# ---------- AI SENTIMENT ----------
def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.05:
        return "Positive"
    elif polarity < -0.05:
        return "Negative"
    else:
        return "Neutral"

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        event = " ".join(request.form["event"].strip().title().split())
        student = request.form["student"]
        rating = int(request.form["rating"])
        comment = request.form["comment"]
        sentiment = analyze_sentiment(comment)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO feedback (event, student, rating, comment, sentiment) VALUES (?,?,?,?,?)",
                (event, student, rating, comment, sentiment)
            )
            conn.commit()
        return render_template("index.html", success=True)
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session["admin"] = True
            return redirect(url_for("admin"))
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    with get_db() as conn:
        data = conn.execute("SELECT * FROM feedback ORDER BY event").fetchall()

    events = defaultdict(list)
    for d in data:
        events[d['event']].append(d)

    event_summary = {}
    for event, rows in events.items():
        total = len(rows)
        avg = round(sum(r['rating'] for r in rows) / total, 2) if total else 0
        pos = len([r for r in rows if r['sentiment'] == "Positive"])
        neg = len([r for r in rows if r['sentiment'] == "Negative"])
        neu = len([r for r in rows if r['sentiment'] == "Neutral"])

        if pos > neg:
            summary_text = "Overall positive response. Majority enjoyed the event."
        elif neg > pos:
            summary_text = "Event received mixed/negative responses. Improvements needed."
        else:
            summary_text = "Event received neutral/mixed feedback overall."

        event_summary[event] = {
            "total": total, "avg": avg, "pos": pos, "neg": neg, "neu": neu,
            "rows": rows, "summary": summary_text
        }

    return render_template("admin.html", event_summary=event_summary)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=8080)