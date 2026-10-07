from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch

import pytest
from openpyxl import load_workbook
from backend import create_app
from backend.extensions import db
from backend.models import (AuthAttempt, Course, CriticalAlert, Enrollment, FormAttempt,
                            FormResponse, Questionnaire, User)
from test_app import app, client, register, login


WRITE = {"X-Requested-With": "XMLHttpRequest"}


def test_admin_registration_requires_proof_even_for_configured_email(client, app):
    with patch("backend.routes.mail.send") as mail:
        response = client.post("/api/auth/register", headers=WRITE, json={"email": "admin@example.com", "name": "Admin", "password": "Segura123!"})
    assert response.status_code == 201
    token = mail.call_args.args[0].body.split("/api/auth/verify/")[1]
    with app.app_context():
        user = User.query.filter_by(email="admin@example.com").one()
        assert user.role == "student" and not user.is_verified
        assert user.verification_token == sha256(token.encode()).hexdigest()
    assert client.post("/api/auth/login", headers=WRITE, json={"email": "admin@example.com", "password": "Segura123!"}).status_code == 403
    assert client.get(f"/api/auth/verify/{token}").status_code == 302
    assert client.get(f"/api/auth/verify/{token}").status_code == 404
    headers = login(client, "admin@example.com")
    assert client.get("/api/me", headers=headers).json["user"]["role"] == "admin"


def test_registration_without_smtp_does_not_create_verified_account(client, app):
    app.config["MAIL_USERNAME"] = ""
    response = client.post("/api/auth/register", headers=WRITE, json={"email": "admin@example.com", "name": "Admin", "password": "Segura123!"})
    assert response.status_code == 503
    with app.app_context(): assert User.query.count() == 0


def test_unapproved_email_is_rejected(client):
    response = client.post("/api/auth/register", headers=WRITE, json={"email": "other@example.com", "name": "Other", "password": "Segura123!"})
    assert response.status_code == 403


def test_verification_expires(client, app):
    with app.app_context():
        user = User(email="student@example.com", name="Student", is_verified=False)
        token = user.issue_verification_token()
        user.verification_issued_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.add(user); db.session.commit()
    assert client.get(f"/api/auth/verify/{token}").status_code == 400


def test_cookies_csrf_logout_and_no_bearer_auth(client):
    register(client, "student@example.com")
    headers = login(client, "student@example.com")
    assert client.post("/api/auth/logout", headers={"Cookie": headers["Cookie"], **WRITE}).status_code == 401
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", headers={**WRITE, "Origin": "https://other.invalid"}, json={}).status_code == 403
    assert client.post("/api/auth/login", json={}).status_code == 403


def test_account_deactivation_and_edit_revoke_sessions(client, app):
    register(client, "student@example.com"); register(client, "admin@example.com")
    student = login(client, "student@example.com"); admin = login(client, "admin@example.com")
    user_id = client.get("/api/me", headers=student).json["user"]["id"]
    assert client.put(f"/api/admin/users/{user_id}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/me", headers=student).status_code == 401
    assert client.put(f"/api/admin/users/{user_id}", headers=admin, json={"is_active": True}).status_code == 200
    assert client.get("/api/me", headers=student).status_code == 401


@pytest.mark.parametrize("verified", [False, None, "false"])
def test_google_requires_verified_email(client, verified):
    with patch("backend.routes.oauth") as oauth:
        oauth.google.authorize_access_token.return_value = {"userinfo": {"email": "admin@example.com", "sub": "google1", "email_verified": verified}}
        assert client.get("/api/auth/google/callback").status_code == 403


def test_google_does_not_leak_token_and_rejects_subject_conflict(client, app):
    with patch("backend.routes.oauth") as oauth:
        oauth.google.authorize_access_token.return_value = {"userinfo": {"email": "admin@example.com", "sub": "google1", "email_verified": True}}
        response = client.get("/api/auth/google/callback")
        assert response.status_code == 302 and "token=" not in response.location
        assert any("HttpOnly" in value for value in response.headers.getlist("Set-Cookie"))
        oauth.google.authorize_access_token.return_value["userinfo"]["sub"] = "different"
        assert client.get("/api/auth/google/callback").status_code == 403


def test_authentication_limits_persist_across_clients(client, app):
    for _ in range(10):
        assert client.post("/api/auth/login", headers=WRITE, json={"email": "missing@example.com", "password": "wrong"}).status_code == 401
    assert app.test_client().post("/api/auth/login", headers=WRITE, json={"email": "missing@example.com"}).status_code == 429
    with app.app_context(): assert all(len(row.key) == 64 for row in AuthAttempt.query.all())


def course_with_response(app, sensitive=True, reviewed=False):
    """Synthetic historical record and alert, never real student data."""
    with app.app_context():
        old = datetime.now(timezone.utc) - timedelta(days=90)
        student = User(email="student@example.com", name="=1+1", is_verified=True)
        student.set_password("Segura123!")
        form = Questionnaire.query.first()
        form.requires_sensitive_approval = sensitive
        version = form.versions[0]
        question = version.aspects[0].questions[0]
        course = Course(name="Prueba", academic_year="2026-2027", level=1, is_active=False, updated_at=old)
        db.session.add_all([student, course]); db.session.flush()
        attempt = FormAttempt(student_id=student.id, course_id=course.id, version_id=version.id, created_at=old)
        db.session.add(attempt); db.session.flush()
        response = FormResponse(attempt_id=attempt.id, question_id=question.id, text_value="=1+1")
        db.session.add(response); db.session.flush()
        alert = CriticalAlert(attempt_id=attempt.id, response_id=response.id, created_at=old, reviewed_at=old if reviewed else None)
        db.session.add(alert); db.session.commit()
        return course.id, attempt.id, alert.id, form.id


def test_sensitive_gate_covers_analytics_alerts_and_exports(client, app):
    course, attempt, alert, _ = course_with_response(app)
    register(client, "admin@example.com"); headers = login(client, "admin@example.com")
    app.config["SENSITIVE_DATA_ENABLED"] = False
    for path in (f"/courses/{course}/form-analytics", f"/courses/{course}/export.xlsx", f"/courses/{course}/export.pdf", f"/attempts/{attempt}/export.pdf", "/attempts"):
        assert client.get("/api" + path, headers=headers).status_code == 403
    assert client.put(f"/api/alerts/{alert}/review", headers=headers, json={"notes": "test"}).status_code == 403


def test_sensitive_review_requires_designation_even_for_admin(client, app):
    course, _, _, _ = course_with_response(app)
    register(client, "admin@example.com"); headers = login(client, "admin@example.com")
    app.config["SENSITIVE_REVIEWER_EMAILS"] = set()
    assert client.get(f"/api/courses/{course}/form-analytics", headers=headers).status_code == 403


def test_ordinary_form_exports_work_without_sensitive_switch_and_use_literal_cells(client, app):
    course, _, _, _ = course_with_response(app, sensitive=False)
    register(client, "admin@example.com"); headers = login(client, "admin@example.com")
    app.config["SENSITIVE_DATA_ENABLED"] = False
    response = client.get(f"/api/courses/{course}/export.xlsx", headers=headers)
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.data))
    assert workbook.active["C2"].value == "=1+1" and workbook.active["C2"].data_type == "s"
    assert workbook.active["I2"].data_type == "s"


def test_retention_preview_requires_review_and_erases_related_data(app):
    course, _, _, _ = course_with_response(app)
    runner = app.test_cli_runner()
    app.config["RETENTION_DAYS"] = ""
    assert runner.invoke(args=["purge-expired"]).exit_code != 0
    app.config["RETENTION_DAYS"] = "30"
    args = ["purge-expired", "--course-id", str(course)]
    assert runner.invoke(args=args + ["--execute"]).exit_code != 0
    with app.app_context():
        alert = CriticalAlert.query.one()
        alert.reviewed_at = datetime.now(timezone.utc) - timedelta(days=60)
        db.session.commit()
    assert runner.invoke(args=args).exit_code == 0
    with app.app_context(): assert FormAttempt.query.count() == 1
    result = runner.invoke(args=args + ["--execute"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        for model in (Course, FormAttempt, FormResponse, CriticalAlert): assert model.query.count() == 0
        assert User.query.count() == 1 and Questionnaire.query.count() > 0


def test_privacy_is_public_and_escaped(client, app):
    app.config["PRIVACY_CONTROLLER"] = "<script>bad()</script>"
    response = client.get("/privacidad")
    assert response.status_code == 200 and b"&lt;script&gt;" in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_insecure_configuration_is_rejected():
    with pytest.raises(RuntimeError): create_app({"SECRET_KEY": "dev-change-me"})


def test_mail_failure_rolls_back_registration(client, app):
    import smtplib
    with patch("backend.routes.mail.send", side_effect=smtplib.SMTPException("test")):
        response = client.post("/api/auth/register", headers=WRITE, json={"email": "student@example.com", "name": "Student", "password": "Segura123!"})
    assert response.status_code == 503
    with app.app_context(): assert User.query.count() == 0


def test_closed_courses_block_legacy_and_versioned_submission(client, app):
    course, _, _, form = course_with_response(app)
    student = login(client, "student@example.com")
    with app.app_context():
        user = User.query.filter_by(email="student@example.com").one()
        version = db.session.get(Questionnaire, form).versions[0].id
        db.session.add(Enrollment(student_id=user.id, course_id=course)); db.session.commit()
    assert client.post(f"/api/courses/{course}/attempts", headers=student, json={"answers": []}).status_code == 403
    assert client.post(f"/api/courses/{course}/forms/{version}/attempts", headers=student, json={"responses": []}).status_code == 403


def test_new_versions_reset_ordinary_classification(client, app):
    register(client, "admin@example.com"); headers = login(client, "admin@example.com")
    created = client.post("/api/admin/questionnaires", headers=headers, json={"name": "Ordinary test", "level": 1}).json
    path = f"/api/admin/questionnaires/{created['id']}"
    assert client.put(path, headers=headers, json={"requires_sensitive_approval": False}).status_code == 200
    assert client.post(path + "/versions", headers=headers, json={}).status_code == 201
    assert client.get(path, headers=headers).json["requires_sensitive_approval"] is True


def test_sensitive_designation_does_not_bypass_course_scope(client, app):
    course, attempt, alert, _ = course_with_response(app)
    with app.app_context():
        tutor = User(email="tutor@example.com", name="Tutor", role="tutor", is_verified=True)
        tutor.set_password("Segura123!"); db.session.add(tutor); db.session.commit()
    headers = login(client, "tutor@example.com")
    for path in (f"/courses/{course}/form-analytics", f"/courses/{course}/export.xlsx", f"/courses/{course}/export.pdf", f"/attempts/{attempt}/export.pdf"):
        assert client.get("/api" + path, headers=headers).status_code == 403
    assert client.put(f"/api/alerts/{alert}/review", headers=headers, json={"notes": "test"}).status_code == 403
