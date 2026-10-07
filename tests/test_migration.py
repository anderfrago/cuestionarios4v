from flask_migrate import upgrade
from sqlalchemy import text
from backend import create_app
from backend.extensions import db


def test_migration_preserves_account_and_closes_old_verification_links(tmp_path):
    app = create_app({"TESTING": True, "AUTO_CREATE_DB": False,
                      "SECRET_KEY": "s" * 48, "JWT_SECRET_KEY": "j" * 48,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'migration.db'}"})
    with app.app_context():
        upgrade(revision="37d102ca7e27")
        db.session.execute(text("INSERT INTO user (id,email,name,role,is_verified,is_active,verification_token) VALUES (1,'existing@example.org','Existing','student',1,1,'old-token')"))
        db.session.execute(text("INSERT INTO course (id,name,academic_year,level,invite_code,is_active) VALUES (1,'Existing course','2026-2027',1,'test-code',0)"))
        db.session.execute(text("INSERT INTO questionnaire (id,name,level,is_archived) VALUES (1,'Existing form',1,0)"))
        db.session.commit()
        upgrade()
        assert tuple(db.session.execute(text("SELECT email, auth_version, verification_token FROM user WHERE id=1")).one()) == ("existing@example.org", 1, None)
        assert db.session.execute(text("SELECT requires_sensitive_approval FROM questionnaire WHERE id=1")).scalar() == 1
        assert db.session.execute(text("SELECT updated_at FROM course WHERE id=1")).scalar() is not None
        db.session.remove(); db.engine.dispose()
