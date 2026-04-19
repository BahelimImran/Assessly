import { Component } from '@angular/core';
import { UploadSyllabusComponent } from './features/upload-syllabus/upload-syllabus.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [UploadSyllabusComponent],
  template: `
    <app-upload-syllabus></app-upload-syllabus>
  `
})
export class AppComponent {}