import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/')) return next(request);
  const headers: Record<string, string> = { 'X-Requested-With': 'XMLHttpRequest' };
  if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
    const csrf = document.cookie.split('; ').find(value => value.startsWith('csrf_access_token='));
    if (csrf) headers['X-CSRF-TOKEN'] = decodeURIComponent(csrf.substring('csrf_access_token='.length));
  }
  return next(request.clone({ withCredentials: true, setHeaders: headers }));
};
