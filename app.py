
from datetime import datetime
import os

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    abort,
)
from flask_sqlalchemy import SQLAlchemy
import plotly.express as px

app = Flask(__name__)

# -------------------- DATABASE --------------------

os.makedirs(app.instance_path, exist_ok=True)
database_path = os.path.join(app.instance_path, "openhospitalflow.db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + database_path.replace("\\", "/")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

STATUSES = [
    "Registered",
    "Waiting",
    "Consultation",
    "Diagnostics",
    "Treatment",
    "Discharged",
]

PRIORITIES = ["Low", "Normal", "High", "Urgent"]


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(30), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Normal")
    status = db.Column(
        db.String(30), nullable=False, default="Registered"
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now
    )

    history = db.relationship(
        "VisitHistory",
        backref="visit",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="VisitHistory.changed_at",
    )


class VisitHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(
        db.Integer, db.ForeignKey("visit.id"), nullable=False
    )
    status = db.Column(db.String(30), nullable=False)
    changed_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now
    )


with app.app_context():
    db.create_all()


# -------------------- ANALYTICS HELPERS --------------------

def minutes_between(start, end):
    return max(0, (end - start).total_seconds() / 60)


def get_wait_minutes(visit):
    """Calculate the first recorded waiting interval."""
    events = sorted(visit.history, key=lambda event: event.changed_at)

    waiting_start = next(
        (
            event.changed_at
            for event in events
            if event.status == "Waiting"
        ),
        None,
    )

    if waiting_start is None:
        return None

    waiting_end = next(
        (
            event.changed_at
            for event in events
            if event.changed_at > waiting_start
            and event.status != "Waiting"
        ),
        None,
    )

    if waiting_end is None:
        waiting_end = datetime.now()

    return minutes_between(waiting_start, waiting_end)


def get_visit_duration(visit):
    """Calculate registration-to-discharge duration."""
    if visit.status != "Discharged":
        return None

    discharge_event = next(
        (
            event
            for event in reversed(visit.history)
            if event.status == "Discharged"
        ),
        None,
    )

    if discharge_event is None:
        return None

    return minutes_between(visit.created_at, discharge_event.changed_at)


def make_bar_chart(x_values, y_values, x_label, y_label, title):
    """Always supply valid x and y data, even when there are no records."""
    if not x_values or not y_values:
        x_values = ["No data yet"]
        y_values = [0]

    fig = px.bar(
        x=x_values,
        y=y_values,
        labels={"x": x_label, "y": y_label},
        title=title,
    )

    fig.update_layout(
        margin=dict(l=25, r=20, t=55, b=75),
        template="plotly_white",
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True},
    )


# -------------------- SHARED PAGE STYLES --------------------

STYLE = """
<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    padding: 24px;
    background: #f3f6fb;
    color: #1f2937;
    font-family: Arial, sans-serif;
}

main { max-width: 1400px; margin: auto; }
h1 { color: #176b87; }

.panel {
    background: white;
    padding: 22px;
    margin-bottom: 22px;
    border-radius: 14px;
    box-shadow: 0 3px 12px #0000000d;
}

.muted { color: #64748b; font-size: 14px; }

nav {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    margin: 18px 0;
}

nav a { color: #176b87; font-weight: bold; }

.form-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}

input, select, button {
    width: 100%;
    padding: 11px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    font-size: 14px;
}

button {
    color: white;
    background: #176b87;
    border: none;
    cursor: pointer;
    font-weight: bold;
}

button:hover { background: #12546b; }
.primary { margin-top: 14px; max-width: 240px; }

.kanban {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    align-items: start;
}

.kanban-column {
    background: #f1f5f9;
    border-radius: 10px;
    padding: 12px;
    min-width: 0;
}

.visit-card {
    background: white;
    border: 1px solid #dbe3ec;
    border-radius: 9px;
    padding: 13px;
    margin-bottom: 10px;
    overflow-wrap: anywhere;
}

.visit-card p { font-size: 13px; margin: 8px 0; }

.count {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    border-radius: 20px;
    padding: 4px 8px;
    font-size: 12px;
}

.priority { font-size: 12px; font-weight: bold; }
.move-button { margin-top: 8px; }
.completed { color: #15803d; font-weight: bold; }

.metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
}

.metric {
    background: #eef6fa;
    padding: 18px;
    border-radius: 10px;
}

.metric strong {
    display: block;
    font-size: 25px;
    margin-top: 8px;
}

.table-wrap, .chart { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; min-width: 650px; }
th, td {
    text-align: left;
    padding: 11px;
    border-bottom: 1px solid #e5e7eb;
}
th { color: #176b87; background: #f8fafc; }

@media (max-width: 900px) {
    .kanban { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .form-grid, .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
    body { padding: 12px; }
    .panel { padding: 15px; }
    .kanban, .form-grid, .metrics { grid-template-columns: 1fr; }
    .primary { max-width: none; }
}
</style>
"""

NAV = """
<nav>
    <a href="{{ url_for('home') }}">Kanban Board</a>
    <a href="{{ url_for('analytics') }}">Analytics Dashboard</a>
</nav>
"""


# -------------------- KANBAN PAGE --------------------

HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenHospitalFlow</title>
""" + STYLE + """
</head>
<body>
<main>
<section class="panel">
    <h1>OpenHospitalFlow</h1>
    <p>Hospital Patient Workflow &amp; Analytics</p>
    <p class="muted">
        Educational project using fictional records only.
        Not for clinical decision-making.
    </p>
    """ + NAV + """
    <strong>Total visits: {{ visits|length }}</strong>
</section>

<section class="panel">
    <h2>Register a Visit</h2>
    <form method="POST" action="{{ url_for('add_visit') }}">
        <div class="form-grid">
            <input name="patient_code" maxlength="30"
                   placeholder="Demo code (e.g. DEMO-001)" required>
            <input name="department" maxlength="80"
                   placeholder="Department (e.g. Cardiology)" required>
            <select name="priority">
                {% for item in priorities %}
                <option value="{{ item }}">{{ item }} Priority</option>
                {% endfor %}
            </select>
            <select name="status">
                {% for item in statuses %}
                <option value="{{ item }}">{{ item }}</option>
                {% endfor %}
            </select>
        </div>
        <button class="primary" type="submit">Register Visit</button>
    </form>
</section>

<section class="panel">
    <h2>Kanban Workflow Board</h2>
    <div class="kanban">
    {% for stage in statuses %}
        <div class="kanban-column">
            <h3>
                {{ stage }}
                <span class="count">
                    {{ visits|selectattr('status', 'equalto', stage)|list|length }}
                </span>
            </h3>

            {% for visit in visits if visit.status == stage %}
            <div class="visit-card">
                <strong>{{ visit.patient_code }}</strong>
                <p>Department: {{ visit.department }}</p>
                <p>Priority: {{ visit.priority }}</p>

                {% if visit.status != "Discharged" %}
                <form method="POST"
                      action="{{ url_for('move_visit', visit_id=visit.id) }}">
                    <button class="move-button" type="submit">
                        Move to {{ statuses[statuses.index(stage) + 1] }} →
                    </button>
                </form>
                {% else %}
                <p class="completed">Visit complete ✓</p>
                {% endif %}

                <p>
                    <a href="{{ url_for('visit_detail', visit_id=visit.id) }}">
                        View history
                    </a>
                </p>
            </div>
            {% else %}
            <p class="muted">No visits in this stage.</p>
            {% endfor %}
        </div>
    {% endfor %}
    </div>
</section>

<section class="panel">
    <h2>All Visits</h2>
    <div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>ID</th><th>Demo Code</th><th>Department</th>
                <th>Priority</th><th>Status</th><th>Created</th><th>History</th>
            </tr>
        </thead>
        <tbody>
        {% for visit in visits %}
            <tr>
                <td>{{ visit.id }}</td>
                <td>{{ visit.patient_code }}</td>
                <td>{{ visit.department }}</td>
                <td>{{ visit.priority }}</td>
                <td>{{ visit.status }}</td>
                <td>{{ visit.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
                <td>
                    <a href="{{ url_for('visit_detail', visit_id=visit.id) }}">
                        View
                    </a>
                </td>
            </tr>
        {% else %}
            <tr><td colspan="7">No visits registered yet.</td></tr>
        {% endfor %}
        </tbody>
    </table>
    </div>
</section>
</main>
</body>
</html>
"""


# -------------------- ANALYTICS PAGE --------------------

ANALYTICS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenHospitalFlow Analytics</title>
<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>
""" + STYLE + """
</head>
<body>
<main>
<section class="panel">
    <h1>Analytics Dashboard</h1>
    <p class="muted">
        Metrics calculated from saved demo visits and recorded status history.
    </p>
    """ + NAV + """
    <div class="metrics">
        <div class="metric">Total visits<strong>{{ total }}</strong></div>
        <div class="metric">Discharged<strong>{{ discharged }}</strong></div>
        <div class="metric">Average waiting<strong>{{ avg_wait }}</strong></div>
        <div class="metric">Average visit duration<strong>{{ avg_duration }}</strong></div>
    </div>
</section>

<section class="panel">
    <h2>Visits by Workflow Stage</h2>
    <div class="chart">{{ status_chart|safe }}</div>
</section>

<section class="panel">
    <h2>Visits by Department</h2>
    <div class="chart">{{ department_chart|safe }}</div>
</section>

<section class="panel">
    <h2>Waiting Time by Visit</h2>
    <div class="chart">{{ waiting_chart|safe }}</div>
    <p class="muted">
        Waiting time is measured from the first recorded Waiting status
        until the next recorded status. Visits without that interval are excluded.
    </p>
</section>
</main>
</body>
</html>
"""


# -------------------- VISIT HISTORY PAGE --------------------

HISTORY_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visit History</title>
""" + STYLE + """
</head>
<body>
<main>
<section class="panel">
    <h1>Visit History: {{ visit.patient_code }}</h1>
    """ + NAV + """
    <p><strong>Department:</strong> {{ visit.department }}</p>
    <p><strong>Current status:</strong> {{ visit.status }}</p>
    <p><strong>Priority:</strong> {{ visit.priority }}</p>

    <h2>Status Timeline</h2>
    <div class="table-wrap">
    <table>
        <thead><tr><th>Status</th><th>Timestamp</th></tr></thead>
        <tbody>
        {% for event in visit.history %}
            <tr>
                <td>{{ event.status }}</td>
                <td>{{ event.changed_at.strftime("%Y-%m-%d %H:%M:%S") }}</td>
            </tr>
        {% else %}
            <tr><td colspan="2">No history recorded for this visit.</td></tr>
        {% endfor %}
        </tbody>
    </table>
    </div>
    <p class="muted">
        Visits created before history tracking was introduced may not have
        a complete timeline.
    </p>
</section>
</main>
</body>
</html>
"""


# -------------------- ROUTES --------------------

@app.route("/")
def home():
    visits = Visit.query.order_by(Visit.created_at.desc()).all()

    return render_template_string(
        HOME_PAGE,
        visits=visits,
        statuses=STATUSES,
        priorities=PRIORITIES,
    )


@app.route("/add", methods=["POST"])
def add_visit():
    patient_code = request.form.get("patient_code", "").strip()
    department = request.form.get("department", "").strip()
    priority = request.form.get("priority", "Normal")
    status = request.form.get("status", "Registered")

    if (
        not patient_code
        or not department
        or priority not in PRIORITIES
        or status not in STATUSES
    ):
        abort(400, "Invalid visit details.")

    visit = Visit(
        patient_code=patient_code,
        department=department,
        priority=priority,
        status=status,
    )

    db.session.add(visit)
    db.session.flush()

    # Save the initial status in the history table.
    db.session.add(
        VisitHistory(visit_id=visit.id, status=status)
    )
    db.session.commit()

    return redirect(url_for("home"))


@app.route("/move/<int:visit_id>", methods=["POST"])
def move_visit(visit_id):
    visit = db.get_or_404(Visit, visit_id)

    if visit.status not in STATUSES:
        abort(400, "Invalid workflow status.")

    current_index = STATUSES.index(visit.status)

    if current_index < len(STATUSES) - 1:
        next_status = STATUSES[current_index + 1]
        visit.status = next_status

        db.session.add(
            VisitHistory(visit_id=visit.id, status=next_status)
        )
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/visit/<int:visit_id>")
def visit_detail(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    return render_template_string(HISTORY_PAGE, visit=visit)


@app.route("/analytics")
def analytics():
    visits = Visit.query.order_by(Visit.created_at.asc()).all()

    total = len(visits)
    discharged = sum(
        1 for visit in visits if visit.status == "Discharged"
    )

    waits = []
    durations = []

    for visit in visits:
        wait = get_wait_minutes(visit)
        duration = get_visit_duration(visit)

        if wait is not None:
            waits.append(wait)

        if duration is not None:
            durations.append(duration)

    avg_wait = (
        f"{sum(waits) / len(waits):.1f} min"
        if waits else "No data yet"
    )
    avg_duration = (
        f"{sum(durations) / len(durations):.1f} min"
        if durations else "No data yet"
    )

    # Chart 1: current visit count by workflow stage.
    status_counts = {
        status: sum(1 for visit in visits if visit.status == status)
        for status in STATUSES
    }

    status_chart = make_bar_chart(
        list(status_counts.keys()),
        list(status_counts.values()),
        "Workflow stage",
        "Number of visits",
        "Current Visits by Workflow Stage",
    )

    # Chart 2: visit count by department.
    department_counts = {}
    for visit in visits:
        department_counts[visit.department] = (
            department_counts.get(visit.department, 0) + 1
        )

    department_chart = make_bar_chart(
        list(department_counts.keys()),
        list(department_counts.values()),
        "Department",
        "Number of visits",
        "Visits by Department",
    )

    # Chart 3: recorded waiting time for each visit.
    waiting_codes = []
    waiting_values = []

    for visit in visits:
        wait = get_wait_minutes(visit)
        if wait is not None:
            waiting_codes.append(visit.patient_code)
            waiting_values.append(round(wait, 1))

    waiting_chart = make_bar_chart(
        waiting_codes,
        waiting_values,
        "Demo visit code",
        "Waiting minutes",
        "Recorded Waiting Time by Visit",
    )

    return render_template_string(
        ANALYTICS_PAGE,
        total=total,
        discharged=discharged,
        avg_wait=avg_wait,
        avg_duration=avg_duration,
        status_chart=status_chart,
        department_chart=department_chart,
        waiting_chart=waiting_chart,
    )


if __name__ == "__main__":
    app.run(debug=True)
