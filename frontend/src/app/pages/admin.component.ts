import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { Course, FormAspect, FormQuestion, FormVersion, Questionnaire, User } from '../core/models';

@Component({
    standalone: true,
     imports: [FormsModule],
     templateUrl: './admin.component.html'
})
export class AdminComponent implements OnInit {
    private api = inject(ApiService);

    tab = signal<'courses' | 'users' | 'forms'>('courses'); courses = signal<Course[]>([]);

    users = signal<User[]>([]); questionnaires = signal<Questionnaire[]>([]);

    selectedForm = signal<Questionnaire | null>(null); version = signal<FormVersion | null>(null);
    message = signal('');
    assigned = signal<Record<number, number[]>>({});

    tutors = () => this.users().filter(u => (u.role === 'tutor' || u.role === 'admin') && u.is_active);

    activeCourses = () => this.courses().filter(c => c.is_active);
    inactiveCourses = () => this.courses().filter(c => !c.is_active);
    activeForms = () => this.questionnaires().filter(f => !f.is_archived);
    archivedForms = () => this.questionnaires().filter(f => f.is_archived);
    newCourse: Partial<Course> = { name: '', academic_year: '2026-2027', level: 1, tutor_id: null }; newForm: Partial<Questionnaire> = { name: '', description: '', level: 1 };
    newUser: { name: string; email: string; password: string; role: 'student' | 'tutor' | 'admin' } = { name: '', email: '', password: '', role: 'student' };

    ngOnInit() {
        this.reload()
    }
    reload() {
        this.api.adminCourses().subscribe(v => { this.courses.set(v); this.assigned.set(Object.fromEntries(v.map(c => [c.id, c.questionnaire_ids || []]))) });
        this.api.users().subscribe(v => this.users.set(v));
        this.api.questionnaires().subscribe(v => { this.questionnaires.set(v); const current = this.selectedForm(); if (current) { const fresh = v.find(x => x.id === current.id) || null; this.selectedForm.set(fresh); if (this.version()) { this.version.set(fresh?.versions?.find(x => x.id === this.version()!.id) || null) } } })
    }
    addCourse() {
        this.api.createCourse(this.newCourse).subscribe(() => this.reload())
    }
    assignTutor(c: Course, id: number | null) {
        this.api.updateCourse(c.id, { tutor_id: id }).subscribe(() => this.reload())
    }
    deleteCourse(c: Course) {
        this.api.deleteCourse(c.id).subscribe({
            next: () => {
                this.message.set('Curso eliminado.'); this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo eliminar el curso')
        })
    }
    restoreCourse(c: Course) {
        this.api.updateCourse(c.id, { is_active: true }).subscribe({
            next: () => {
                this.message.set('Curso restaurado.'); this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo restaurar el curso')
        })
    }
    permanentlyDeleteCourse(c: Course) {
        if (!confirm(`¿Borrar definitivamente el curso ${c.name} y todos los formularios completados en él? Esta acción no se puede deshacer.`)) return;
        this.api.permanentlyDeleteCourse(c.id).subscribe({
            next: () => {
                this.message.set('Curso y formularios completados borrados definitivamente.');
                this.reload()
            }, error: e => this.message.set(e.error?.error || 'No se pudo borrar definitivamente el curso')
        })
    }
    addUser() {
        this.api.createUser(this.newUser).subscribe({
            next: () => {
                this.newUser = { name: '', email: '', password: '', role: 'student' }; this.message.set('Usuario creado.');
                this.reload()
            }, error: e => this.message.set(e.error?.error || 'No se pudo crear el usuario')
        })
    }
    activateUser(u: User) {
        this.api.updateUser(u.id, { is_verified: true, is_active: true }).subscribe({
            next: () => {
                this.message.set('Cuenta activada sin confirmación por correo.'); this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo activar la cuenta')
        })
    }
    updateUser(u: User, d: Partial<User>) {
        this.api.updateUser(u.id, d).subscribe({
            next: () => {
                this.message.set('Usuario actualizado.');
                this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo actualizar el usuario')
        })
    }
    deleteUser(u: User) {
        this.api.deleteUser(u.id).subscribe({
            next: () => {
                this.message.set('Usuario desactivado.'); this.reload()
            }
            ,
            error: e => this.message.set(e.error?.error || 'No se pudo eliminar el usuario')
        })
    }
    permanentlyDeleteUser(u: User) {
        if (!confirm(`¿Borrar definitivamente a ${u.name} y todos sus formularios completados? Esta acción no se puede deshacer.`))
            return;
        this.api.permanentlyDeleteUser(u.id).subscribe({
            next: () => {
                this.message.set('Usuario y formularios completados borrados definitivamente.');
                this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo borrar definitivamente el usuario')
        })
    }
    formsForLevel(
        level: number) { return this.questionnaires().filter(f => f.level === level && !f.is_archived && f.published_version_id) }
    isAssigned(c: Course, f: Questionnaire) {
        return (this.assigned()[c.id] || []).includes(f.id)
    }
    toggleAssignment(c: Course, f: Questionnaire) {
        const ids = new Set(this.assigned()[c.id] || []); ids.has(f.id) ? ids.delete(f.id) : ids.add(f.id); this.api.assignForms(c.id, [...ids]).subscribe(() => this.assigned.update(v => ({ ...v, [c.id]: [...ids] })))
    }
    addForm() {
        this.api.createQuestionnaire(this.newForm).subscribe(f => { this.newForm = { name: '', description: '', level: 1 }; this.reload(); this.selectForm(f) })
    }
    saveClassification(f: Questionnaire) {
        if (!confirm('Confirma que esta clasificación ha sido revisada por el centro. Los formularios con datos de salud deben mantener activada la autorización específica.')) return;
        this.api.updateQuestionnaire(f.id, {requires_sensitive_approval: f.requires_sensitive_approval}).subscribe({next: () => this.message.set('Clasificación guardada.'), error: e => this.message.set(e.error?.error || 'No se pudo guardar')});
    }
    selectForm(f: Questionnaire) {
        this.selectedForm.set(f);
        this.version.set(f.versions?.find(v => v.status === 'draft') || f.versions?.at(-1) || null)
    }
    duplicateForm(f: Questionnaire) {
        const name = prompt('Nombre del nuevo formulario', `Copia de ${f.name}`)?.trim();
        if (!name) return; this.api.duplicateQuestionnaire(f.id, name).subscribe({
            next: copy => {
                this.message.set('Formulario duplicado. La copia está en borrador y ya puedes modificarla.');
                this.reload();
                this.selectForm(copy)
            },
            error: e => this.message.set(e.error?.error || 'No se pudo duplicar el formulario')
        })
    }
    archiveForm(f: Questionnaire) {
        this.api.archiveQuestionnaire(f.id).subscribe(() => {
            this.message.set('Formulario eliminado. Puedes restaurarlo desde la lista de eliminados.');
            this.selectedForm.set(null); this.version.set(null); this.reload()
        })
    }
    restoreForm(f: Questionnaire) {
        this.api.restoreQuestionnaire(f.id).subscribe(() => {
            this.message.set('Formulario restaurado.');
            this.reload()
        })
    }
    permanentlyDeleteForm(f: Questionnaire) {
        if (!confirm(`¿Borrar definitivamente ${f.name} y todos sus formularios completados? Esta acción no se puede deshacer.`))
            return;
        this.api.permanentlyDeleteQuestionnaire(f.id).subscribe({
            next: () => {
                this.message.set('Formulario y respuestas borrados definitivamente.');
                this.reload()
            },
            error: e => this.message.set(e.error?.error || 'No se pudo borrar definitivamente el formulario')
        })
    }
    newVersion(f: Questionnaire) {
        this.api.createVersion(f.id, f.published_version_id || undefined).subscribe(v => {
            this.reload();
            this.version.set(v)
        })
    }
    publish(v: FormVersion) {
        this.api.publishVersion(v.id).subscribe(() => {
            this.message.set('Versión publicada. Los intentos anteriores conservan su estructura.');
            this.reload()
        })
    }
    addAspect(v: FormVersion) {
        this.api.createFormAspect(v.id, 'Nuevo aspecto').subscribe(() => this.reload())
    }

    saveAspect(a: FormAspect) {
        this.api.updateFormAspect(a.id, a).subscribe(() => this.reload())
    }
    removeAspect(a: FormAspect) { this.api.archiveFormAspect(a.id).subscribe(() => this.reload()) }
    addQuestion(a: FormAspect) {

        this.api.createQuestion(a.id, { title: 'Nueva pregunta', question_type: 'radio', required: true, is_scored: true }).subscribe(() => this.reload())
    }
    saveQuestion(q: FormQuestion) { this.api.updateQuestion(q.id, q).subscribe(() => { this.message.set('Pregunta guardada'); this.reload() }) }
    removeQuestion(q: FormQuestion) {
        this.api.archiveQuestion(q.id).subscribe(() => this.reload())
    }
    move(q: FormQuestion, d: 'up' | 'down') {
        this.api.moveQuestion(q.id, d).subscribe(() => this.reload())
    }
    addOption(q: FormQuestion) {
        q.options.push({ label: '', value: String(q.options.length + 1), score: null })
    }
}
