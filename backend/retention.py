from datetime import datetime, timedelta, timezone
import click
from .extensions import db
from .models import Attempt, Course, CourseQuestionnaire, CriticalAlert, Enrollment, FormAttempt


def register_retention(app):
    @app.cli.command("purge-expired")
    @click.option("--course-id", multiple=True, type=int)
    @click.option("--execute", is_flag=True)
    def purge_expired(course_id, execute):
        """Vista previa de cursos cerrados. Borrado solo con selección explícita."""
        from .routes import delete_form_attempts, delete_legacy_attempts
        try:
            days = int(app.config["RETENTION_DAYS"])
            if days <= 0: raise ValueError
        except (TypeError, ValueError):
            raise click.ClickException("Define RETENTION_DAYS como entero positivo aprobado por el centro")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        eligible = []
        for course in Course.query.filter_by(is_active=False):
            alerts = CriticalAlert.query.join(FormAttempt).filter(FormAttempt.course_id == course.id).all()
            # Unreviewed alerts always require a human decision before scheduled erasure.
            if any(alert.reviewed_at is None for alert in alerts): continue
            dates = [course.updated_at]
            dates += [a.created_at for a in Attempt.query.filter_by(course_id=course.id)]
            dates += [a.created_at for a in FormAttempt.query.filter_by(course_id=course.id)]
            dates += [e.joined_at for e in Enrollment.query.filter_by(course_id=course.id)]
            dates += [a.assigned_at for a in CourseQuestionnaire.query.filter_by(course_id=course.id)]
            dates += [a.reviewed_at for a in alerts]
            if max(d.replace(tzinfo=timezone.utc) for d in dates if d) < cutoff:
                eligible.append(course)
        selected = set(course_id)
        if selected - {c.id for c in eligible}:
            raise click.ClickException("Hay cursos no elegibles, activos o con alertas pendientes. No se ha borrado nada")
        if execute and not selected:
            raise click.ClickException("Indica cada --course-id revisado antes de ejecutar")
        targets = [c for c in eligible if not selected or c.id in selected]
        for course in targets:
            click.echo(f"Curso {course.id}: {Attempt.query.filter_by(course_id=course.id).count()} intentos históricos y {FormAttempt.query.filter_by(course_id=course.id).count()} formularios")
            if execute:
                delete_form_attempts(FormAttempt.query.filter_by(course_id=course.id))
                delete_legacy_attempts(Attempt.query.filter_by(course_id=course.id))
                Enrollment.query.filter_by(course_id=course.id).delete()
                # ORM cascade deletes questionnaire assignments without double deletion.
                db.session.delete(course)
        if execute: db.session.commit()
        click.echo(f"{'Borrados' if execute else 'Vista previa sin borrado'}: {len(targets)} cursos. Cuentas y plantillas conservadas.")
