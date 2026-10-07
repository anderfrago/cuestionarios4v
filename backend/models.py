from datetime import datetime, timezone
from secrets import token_urlsafe
import hashlib
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db


def now():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default="student")
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    auth_version = db.Column(db.Integer, nullable=False, default=1)
    google_subject = db.Column(db.String(255), unique=True)
    verification_issued_at = db.Column(db.DateTime(timezone=True))
    verification_token = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return bool(self.password_hash and check_password_hash(self.password_hash, password))

    def issue_verification_token(self):
        token = token_urlsafe(32)
        self.verification_token = hashlib.sha256(token.encode()).hexdigest()
        self.verification_issued_at = now()
        return token

    def as_dict(self):
        return {"id": self.id, "email": self.email, "name": self.name,
                "role": self.role, "is_verified": self.is_verified, "is_active": self.is_active}


class Course(db.Model):
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    academic_year = db.Column(db.String(9), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    invite_code = db.Column(db.String(32), unique=True, nullable=False, default=lambda: token_urlsafe(10))
    tutor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    tutor = db.relationship("User", foreign_keys=[tutor_id])
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    questionnaire_assignments = db.relationship("CourseQuestionnaire", cascade="all, delete-orphan",
                                                lazy="select")

    def as_dict(self):
        return {"id": self.id, "name": self.name, "academic_year": self.academic_year,
                "level": self.level, "invite_code": self.invite_code, "tutor_id": self.tutor_id,
                "tutor": self.tutor.as_dict() if self.tutor else None, "is_active": self.is_active,
                "questionnaire_ids": [a.questionnaire_id for a in self.questionnaire_assignments if a.is_active]}


class Enrollment(db.Model):
    __table_args__ = (db.UniqueConstraint("student_id", "course_id"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), default=now)
    student = db.relationship("User")
    course = db.relationship("Course")


class Aspect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="")
    order = db.Column(db.Integer, default=0)
    low_max = db.Column(db.Float, default=1.99)
    medium_max = db.Column(db.Float, default=2.99)
    low_message = db.Column(db.Text, default="Estás empezando: cada pequeño paso cuenta.")
    medium_message = db.Column(db.Text, default="Vas avanzando. Mantén la constancia.")
    high_message = db.Column(db.Text, default="Has construido una base sólida. Sigue creciendo.")
    items = db.relationship("Item", backref="aspect", cascade="all, delete-orphan", order_by="Item.order")

    def as_dict(self, include_items=True):
        data = {"id": self.id, "level": self.level, "name": self.name,
                "description": self.description, "order": self.order,
                "low_max": self.low_max, "medium_max": self.medium_max,
                "messages": {"incipiente": self.low_message, "en_desarrollo": self.medium_message,
                             "generado": self.high_message}}
        if include_items:
            data["items"] = [i.as_dict() for i in self.items]
        return data


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aspect_id = db.Column(db.Integer, db.ForeignKey("aspect.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    reverse_scored = db.Column(db.Boolean, default=False)
    help_text = db.Column(db.Text, default="")

    def as_dict(self):
        return {"id": self.id, "aspect_id": self.aspect_id, "text": self.text,
                "order": self.order, "reverse_scored": self.reverse_scored, "help_text": self.help_text}


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    encouragement = db.Column(db.Text, default="")
    student = db.relationship("User")
    course = db.relationship("Course")
    answers = db.relationship("Answer", backref="attempt", cascade="all, delete-orphan")


class Answer(db.Model):
    __table_args__ = (db.UniqueConstraint("attempt_id", "item_id"),)
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("attempt.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=True)
    value = db.Column(db.Integer, nullable=True)
    item = db.relationship("Item")


class Questionnaire(db.Model):
    requires_sensitive_approval = db.Column(db.Boolean, nullable=False, default=True)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    level = db.Column(db.Integer, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    versions = db.relationship("QuestionnaireVersion", backref="questionnaire",
                               cascade="all, delete-orphan", order_by="QuestionnaireVersion.version")

    @property
    def published_version(self):
        return next((v for v in reversed(self.versions) if v.status == "published"), None)

    def as_dict(self, include_versions=False):
        data = {"id": self.id, "name": self.name, "description": self.description,
                "level": self.level, "is_archived": self.is_archived,
                "requires_sensitive_approval": self.requires_sensitive_approval,
                "published_version_id": self.published_version.id if self.published_version else None}
        if include_versions:
            data["versions"] = [v.as_dict() for v in self.versions]
        return data


class QuestionnaireVersion(db.Model):
    __table_args__ = (db.UniqueConstraint("questionnaire_id", "version"),)
    id = db.Column(db.Integer, primary_key=True)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey("questionnaire.id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="draft", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    published_at = db.Column(db.DateTime(timezone=True))
    aspects = db.relationship("FormAspect", backref="version", cascade="all, delete-orphan",
                              order_by="FormAspect.order")

    def as_dict(self, include_structure=True):
        data = {"id": self.id, "questionnaire_id": self.questionnaire_id,
                "version": self.version, "status": self.status,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "published_at": self.published_at.isoformat() if self.published_at else None}
        if include_structure:
            data["aspects"] = [a.as_dict() for a in self.aspects if not a.is_archived]
        return data


class FormAspect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_version.id"), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    order = db.Column(db.Integer, default=0)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    low_max = db.Column(db.Float, default=1.99)
    medium_max = db.Column(db.Float, default=2.99)
    low_message = db.Column(db.Text, default="Estás empezando: cada pequeño paso cuenta.")
    medium_message = db.Column(db.Text, default="Vas avanzando. Mantén la constancia.")
    high_message = db.Column(db.Text, default="Has construido una base sólida. Sigue creciendo.")
    questions = db.relationship("Question", backref="form_aspect", cascade="all, delete-orphan",
                                order_by="Question.order")

    def as_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "order": self.order, "is_archived": self.is_archived,
                "low_max": self.low_max, "medium_max": self.medium_max,
                "messages": {"incipiente": self.low_message, "en_desarrollo": self.medium_message,
                             "generado": self.high_message},
                "questions": [q.as_dict() for q in self.questions if not q.is_archived]}


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aspect_id = db.Column(db.Integer, db.ForeignKey("form_aspect.id"), nullable=False)
    title = db.Column(db.Text, nullable=False)
    help_text = db.Column(db.Text, default="")
    question_type = db.Column(db.String(30), nullable=False, default="radio")
    required = db.Column(db.Boolean, default=True, nullable=False)
    order = db.Column(db.Integer, default=0)
    reverse_scored = db.Column(db.Boolean, default=False, nullable=False)
    is_scored = db.Column(db.Boolean, default=True, nullable=False)
    allow_other = db.Column(db.Boolean, default=False, nullable=False)
    is_critical = db.Column(db.Boolean, default=False, nullable=False)
    critical_score_min = db.Column(db.Float)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    options = db.relationship("QuestionOption", backref="question", cascade="all, delete-orphan",
                              order_by="QuestionOption.order")
    rows = db.relationship("QuestionRow", backref="question", cascade="all, delete-orphan",
                           order_by="QuestionRow.order")

    def as_dict(self):
        return {"id": self.id, "aspect_id": self.aspect_id, "title": self.title,
                "help_text": self.help_text, "question_type": self.question_type,
                "required": self.required, "order": self.order,
                "reverse_scored": self.reverse_scored, "is_scored": self.is_scored,
                "allow_other": self.allow_other, "is_critical": self.is_critical,
                "critical_score_min": self.critical_score_min, "is_archived": self.is_archived,
                "options": [o.as_dict() for o in self.options if not o.is_archived],
                "rows": [r.as_dict() for r in self.rows if not r.is_archived]}


class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    label = db.Column(db.String(300), nullable=False)
    value = db.Column(db.String(120), nullable=False)
    score = db.Column(db.Float)
    order = db.Column(db.Integer, default=0)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    def as_dict(self):
        return {"id": self.id, "label": self.label, "value": self.value,
                "score": self.score, "order": self.order, "is_archived": self.is_archived}


class QuestionRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    label = db.Column(db.String(400), nullable=False)
    order = db.Column(db.Integer, default=0)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    def as_dict(self):
        return {"id": self.id, "label": self.label, "order": self.order,
                "is_archived": self.is_archived}


class CourseQuestionnaire(db.Model):
    __table_args__ = (db.UniqueConstraint("course_id", "questionnaire_id"),)
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey("questionnaire.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), default=now)
    questionnaire = db.relationship("Questionnaire")


class FormAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_version.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    encouragement = db.Column(db.Text, default="")
    student = db.relationship("User")
    course = db.relationship("Course")
    version = db.relationship("QuestionnaireVersion")
    responses = db.relationship("FormResponse", backref="attempt", cascade="all, delete-orphan")


class FormResponse(db.Model):
    __table_args__ = (db.UniqueConstraint("attempt_id", "question_id", "row_id"),)
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("form_attempt.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    row_id = db.Column(db.Integer, db.ForeignKey("question_row.id"))
    option_id = db.Column(db.Integer, db.ForeignKey("question_option.id"))
    text_value = db.Column(db.Text)
    score = db.Column(db.Float)
    question = db.relationship("Question")
    row = db.relationship("QuestionRow")
    option = db.relationship("QuestionOption")


class CriticalAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("form_attempt.id"), nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey("form_response.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    reviewed_at = db.Column(db.DateTime(timezone=True))
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    review_notes = db.Column(db.Text, default="")
    attempt = db.relationship("FormAttempt")
    response = db.relationship("FormResponse")
    reviewed_by = db.relationship("User")

    def as_dict(self):
        return {"id": self.id, "created_at": self.created_at.isoformat(),
                "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
                "review_notes": self.review_notes, "student": self.attempt.student.as_dict(),
                "course": self.attempt.course.as_dict(), "question": self.response.question.title,
                "answer": self.response.option.label if self.response.option else self.response.text_value,
                "attempt_id": self.attempt_id}


class AuthAttempt(db.Model):
    __tablename__ = "auth_attempts"
    key = db.Column(db.String(64), primary_key=True)
    hits = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
