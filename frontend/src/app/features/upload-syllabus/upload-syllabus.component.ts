import { ChangeDetectorRef, Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-upload-syllabus',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './upload-syllabus.component.html'
})
export class UploadSyllabusComponent {

  selectedFile: File | null = null;
  message = '';
  isUploading = false;
  
  // NEW
  question: string = '';
  answer: string = '';
  isIngested: boolean = false;
  isQuerying: boolean = false;

  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    }
  }

  uploadFile() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.isUploading = true;

    this.http.post('http://localhost:8000/ingest', formData)
      .subscribe({
        next: (res: any) => {
          this.message = 'Upload + Ingestion successful!';
          this.isUploading = false;
           
          // ENABLE QUESTION FIELD
          this.isIngested = true;
          
          this.cd.detectChanges();
        },
        error: (err) => {
          this.message = 'Upload failed';
          this.isUploading = false;
          console.error(err);
        }
      });
  }

    // 🔥 NEW FUNCTION
  getAnswer() {
    // this.cd.detectChanges();
    if (!this.question) return;

    this.isQuerying = true;

    this.http.post('http://localhost:8000/query', {
      question: this.question
    }).subscribe({
      next: (res: any) => {
        this.answer = res.answer || 'No answer found';
        this.isQuerying = false;
        this.cd.detectChanges();
      },
      error: (err) => {
        this.answer = 'Error fetching answer';
        this.isQuerying = false;
        console.error(err);
      }
    });
  }
}