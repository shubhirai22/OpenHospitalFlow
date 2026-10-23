
import pytest

from app import app, db, Visit, VisitHistory


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"

    with app.app_context():
        db.create_all()

        with app.test_client() as test_client:
            yield test_client

        db.session.remove()
        db.drop_all()


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"OpenHospitalFlow" in response.data
    assert b"Kanban Workflow Board" in response.data


def test_register_visit(client):
    response = client.post(
        "/add",
        data={
            "patient_code": "DEMO-TEST-001",
            "department": "Cardiology",
            "priority": "Normal",
            "status": "Registered",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        visit = Visit.query.filter_by(
            patient_code="DEMO-TEST-001"
        ).first()

        assert visit is not None
        assert visit.department == "Cardiology"
        assert visit.status == "Registered"


def test_moving_visit_records_history(client):
    client.post(
        "/add",
        data={
            "patient_code": "DEMO-TEST-002",
            "department": "Emergency",
            "priority": "High",
            "status": "Registered",
        },
    )

    with app.app_context():
        visit = Visit.query.filter_by(
            patient_code="DEMO-TEST-002"
        ).first()
        visit_id = visit.id

    response = client.post(
        f"/move/{visit_id}",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        visit = db.session.get(Visit, visit_id)

        assert visit.status == "Waiting"
        assert len(visit.history) == 2
        assert visit.history[0].status == "Registered"
        assert visit.history[1].status == "Waiting"


def test_analytics_page_loads_without_visits(client):
    response = client.get("/analytics")

    assert response.status_code == 200
    assert b"Analytics Dashboard" in response.data
    assert b"No data yet" in response.data


def test_invalid_priority_is_rejected(client):
    response = client.post(
        "/add",
        data={
            "patient_code": "DEMO-TEST-003",
            "department": "Cardiology",
            "priority": "InvalidPriority",
            "status": "Registered",
        },
    )

    assert response.status_code == 400
