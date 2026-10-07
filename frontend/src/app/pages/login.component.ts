import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../core/api.service';
@Component({
    standalone: true,
    imports: [FormsModule],
    templateUrl: './login.component.html'
})
export class LoginComponent {
    private api = inject(ApiService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    mode = signal<'login' | 'register'>('login');
    busy = signal(false); message = signal('');
    error = signal(false);
    name = '';
    email = '';
    password = '';

    constructor() {
        if (this.route.snapshot.queryParamMap.get('verified')) this.message.set('Correo verificado. Ya puedes iniciar sesión.');
        const google = this.route.snapshot.queryParamMap.get('google');
        if (google) {
            this.api.loadMe().subscribe(() => this.router.navigate(['/panel']))
        }
    } submit() {
        this.busy.set(true);
        this.message.set(''); const obs = this.mode() === 'login' ? this.api.login(this.email, this.password) : this.api.register({ name: this.name, email: this.email, password: this.password });
        obs.subscribe({
            next: () => {
                this.busy.set(false);
                if (this.mode() === 'login') this.router.navigate(['/panel']);
                else this.message.set('Cuenta creada. Revisa tu correo para verificarla.')
            }, error: e => {
                this.busy.set(false); this.error.set(true);
                this.message.set(e.error?.error || 'No se pudo completar la operación')
            }
        })
    }
}
