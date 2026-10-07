from flask import abort, current_app
from .models import Attempt, FormAttempt


def sensitive_enabled():
    return current_app.config["SENSITIVE_DATA_ENABLED"]


def require_sensitive_access(questionnaire=None):
    if questionnaire is None or questionnaire.requires_sensitive_approval:
        if not sensitive_enabled():
            abort(403, description="Este tratamiento está pendiente de autorización específica del centro")
        from .auth import current_user
        user = current_user()
        if user and user.role != "student" and user.email not in current_app.config["SENSITIVE_REVIEWER_EMAILS"]:
            abort(403, description="No estás designado para revisar datos sensibles")


def require_course_data_access(course):
    if Attempt.query.filter_by(course_id=course.id).first():
        require_sensitive_access()
    for attempt in FormAttempt.query.filter_by(course_id=course.id):
        require_sensitive_access(attempt.version.questionnaire)
