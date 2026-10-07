import { HttpClient } from '@angular/common/http';

import { Injectable, computed, inject, signal } from '@angular/core';

import { tap } from 'rxjs';
import { Router } from '@angular/router';

import { Aspect, Attempt, Course, CriticalAlert, FormAspect, FormQuestion, FormResponseInput, FormVersion, Questionnaire, User } from './models';


@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  readonly user = signal<User | null>(null);

  readonly sessionError = signal('');
  private router = inject(Router);

  constructor() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  readonly courses = signal<Course[]>([]);

  readonly attempts = signal<Attempt[]>([]);

  readonly loggedIn = computed(() => !!this.user());

  readonly role = computed(() => this.user()?.role ?? null);


  login(email: string, password: string) {
    return this.http.post<{
      user: User
    }>('/api/auth/login', { email, password }).pipe(tap(r => {
      this.user.set(r.user)
    }));
  }
  register(data: {
    name: string;
    email: string;
    password: string
  }) {
    return this.http.post('/api/auth/register', data);
  }
  logout() {
    this.sessionError.set('');
    const clear = () => {this.user.set(null); this.courses.set([]); this.attempts.set([]); this.router.navigateByUrl('/acceso');};
    this.http.post('/api/auth/logout', {}).subscribe({
      next: clear,
      error: error => error.status === 401 ? clear() : this.sessionError.set('No se ha podido cerrar la sesión. Comprueba la conexión e inténtalo de nuevo.')
    });
  }
  loadMe() {
    return this.http.get<{
      user: User;
      courses: Course[]
    }>('/api/me').pipe(tap(r => {
      this.user.set(r.user);
      this.courses.set(r.courses)
    }));
  }
  join(code: string) {
    return this.http.post<Course>('/api/courses/join', { code }).pipe(tap(c => this.courses.update(v => [...v.filter(x => x.id !== c.id), c])));
  }
  questionnaire(courseId: number) {
    return this.http.get<{
      course: Course;
      scale: {
        value: number;
        label: string
      }[];
      aspects: Aspect[]
    }>(`/api/courses/${courseId}/questionnaire`);
  }
  submit(courseId: number, answers: {
    item_id: number;
    value: number
  }[]) {
    return this.http.post<Attempt>(`/api/courses/${courseId}/attempts`, { answers });
  }
  loadAttempts() {
    return this.http.get<Attempt[]>('/api/attempts').pipe(tap(v => this.attempts.set(v)));
  }
  analytics(courseId: number) {
    return this.http.get<{
      course: Course;
      summary: {
        aspect: string;
        average: number;
        count: number
      }[];
      attempts: Attempt[]
    }>(`/api/courses/${courseId}/analytics`);
  }
  adminCourses() {
    return this.http.get<Course[]>('/api/admin/courses');
  }
  createCourse(data: Partial<Course>) {
    return this.http.post<Course>('/api/admin/courses', data);
  }
  updateCourse(id: number, data: Partial<Course>) {
    return this.http.put<Course>(`/api/admin/courses/${id}`, data);
  }
  deleteCourse(id: number) {
    return this.http.delete(`/api/admin/courses/${id}`);
  }
  permanentlyDeleteCourse(id: number) {
    return this.http.delete(`/api/admin/courses/${id}?permanent=true`);
  }
  users() {
    return this.http.get<User[]>('/api/admin/users');
  }
  createUser(data: Partial<User> & { password?: string }) {
    return this.http.post<User>('/api/admin/users', data);
  }
  updateUser(id: number, data: Partial<User>) {
    return this.http.put<User>(`/api/admin/users/${id}`, data);
  }
  deleteUser(id: number) {
    return this.http.delete(`/api/admin/users/${id}`);
  }
  permanentlyDeleteUser(id: number) {
    return this.http.delete(`/api/admin/users/${id}?permanent=true`);
  }
  aspects() {
    return this.http.get<Aspect[]>('/api/admin/aspects');
  }
  updateAspect(id: number, data: Partial<Aspect> & Record<string, unknown>) {
    return this.http.put<Aspect>(`/api/admin/aspects/${id}`, data);
  }
  createItem(data: Partial<import('./models').Item>) {
    return this.http.post('/api/admin/items', data);
  }
  updateItem(id: number, data: Partial<import('./models').Item>) {
    return this.http.put(`/api/admin/items/${id}`, data);
  }
  questionnaires() {
    return this.http.get<Questionnaire[]>('/api/admin/questionnaires');
  }
  createQuestionnaire(data: Partial<Questionnaire>) {
    return this.http.post<Questionnaire>('/api/admin/questionnaires', data);
  }
  updateQuestionnaire(id: number, data: Partial<Questionnaire>) {
    return this.http.put<Questionnaire>(`/api/admin/questionnaires/${id}`, data);
  }
  archiveQuestionnaire(id: number) {
    return this.http.delete(`/api/admin/questionnaires/${id}`);
  }
  permanentlyDeleteQuestionnaire(id: number) {
    return this.http.delete(`/api/admin/questionnaires/${id}?permanent=true`);
  }
  restoreQuestionnaire(id: number) {
    return this.http.put<Questionnaire>(`/api/admin/questionnaires/${id}`, { is_archived: false });
  }
  createVersion(id: number, source_version_id?: number) {
    return this.http.post<FormVersion>(`/api/admin/questionnaires/${id}/versions`, { source_version_id });
  }
  duplicateQuestionnaire(id: number, name: string) {
    return this.http.post<Questionnaire>(`/api/admin/questionnaires/${id}/duplicate`, { name });
  }
  publishVersion(id: number) {
    return this.http.post<FormVersion>(`/api/admin/versions/${id}/publish`, {});
  }
  createFormAspect(versionId: number, name: string) {
    return this.http.post<FormAspect>(`/api/admin/versions/${versionId}/aspects`, { name });
  }
  updateFormAspect(id: number, data: Partial<FormAspect>) {
    return this.http.put<FormAspect>(`/api/admin/form-aspects/${id}`, data);
  }
  archiveFormAspect(id: number) {
    return this.http.delete(`/api/admin/form-aspects/${id}`);
  }
  createQuestion(aspectId: number, data: Partial<FormQuestion>) {
    return this.http.post<FormQuestion>(`/api/admin/form-aspects/${aspectId}/questions`, data);
  }
  updateQuestion(id: number, data: Partial<FormQuestion>) {
    return this.http.put<FormQuestion>(`/api/admin/questions/${id}`, data);
  }
  archiveQuestion(id: number) {
    return this.http.delete(`/api/admin/questions/${id}`);
  }
  moveQuestion(id: number, direction: 'up' | 'down') {
    return this.http.post<FormQuestion>(`/api/admin/questions/${id}/move`, { direction });
  }
  assignForms(courseId: number, questionnaire_ids: number[]) {
    return this.http.put(`/api/admin/courses/${courseId}/questionnaires`, { questionnaire_ids });
  }
  courseForms(courseId: number) {
    return this.http.get<{
      course: Course;
      forms: Questionnaire[]
    }>(`/api/courses/${courseId}/forms`);
  }
  formDefinition(courseId: number, versionId: number) {
    return this.http.get<{
      course: Course;
      questionnaire: Questionnaire;
      version: FormVersion
    }>(`/api/courses/${courseId}/forms/${versionId}`);
  }
  submitForm(courseId: number, versionId: number, responses: FormResponseInput[]) {
    return this.http.post<Attempt>(`/api/courses/${courseId}/forms/${versionId}/attempts`, { responses });
  }
  formAnalytics(courseId: number) {
    return this.http.get<{
      course: Course;
      summary: {
        aspect: string;
        average: number;
        count: number
      }[];
      attempts: (Attempt & { responses: unknown[] })[];
      alerts: CriticalAlert[]
    }>(`/api/courses/${courseId}/form-analytics`);
  }
  reviewAlert(id: number, notes: string) {
    return this.http.put<CriticalAlert>(`/api/alerts/${id}/review`, { notes });
  }
  download(url: string, filename: string) {
    this.http.get(url, { responseType: 'blob' }).subscribe(blob => {
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(href)
    });
  }
}
