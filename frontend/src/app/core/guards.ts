import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { ApiService } from './api.service';
const check = (roles?: string[]) => {
  const api = inject(ApiService), router = inject(Router);
  return api.loadMe().pipe(map(value => !roles || roles.includes(value.user.role) ? true : router.createUrlTree(['/panel'])),
    catchError(() => {api.user.set(null); api.courses.set([]); api.attempts.set([]); return of(router.createUrlTree(['/acceso']));}));
};
export const authGuard = () => check();
export const roleGuard = (roles: string[]) => () => check(roles);
