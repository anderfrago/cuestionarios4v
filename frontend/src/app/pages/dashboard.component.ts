import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
@Component({
    standalone: true,
    imports: [FormsModule, RouterLink, DatePipe],
    templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
    api = inject(ApiService);
    code = '';
    msg = signal('');
    ngOnInit() {
        this.api.loadMe().subscribe();
        if (this.api.role() === 'student')
            this.api.loadAttempts().subscribe({error: e => {this.api.attempts.set([]); if(e.status !== 403) this.msg.set('No se ha podido cargar el historial.');}})
    } join() {
        this.api.join(this.code).subscribe({
            next: () => {
                this.msg.set('Te has unido correctamente.');
                this.code = ''
            }, error: e => this.msg.set(e.error?.error || 'Código no válido')
        })
    }
}
