import { Component, inject } from '@angular/core';

import { Router, RouterLink, RouterOutlet } from '@angular/router';

import { ApiService } from './core/api.service';

@Component({
    selector:'app-root',
    imports:[RouterOutlet,RouterLink],
    templateUrl:'./app.component.html'
})
export class AppComponent { api=inject(ApiService);
 router=inject(Router);
 logout(){this.api.logout();

} }
