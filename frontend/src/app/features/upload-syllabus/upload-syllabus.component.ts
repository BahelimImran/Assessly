import { ChangeDetectorRef, Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-upload-syllabus',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './upload-syllabus.component.html',
  styleUrls: ['./upload-syllabus.component.css']
})
export class UploadSyllabusComponent {

  selectedFile: File | null = null;
  message = '';
  isUploading = false;

  question: string = '';
  answer: string = '';
  isIngested: boolean = false;
  isQuerying: boolean = false;

  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.message = `Selected: ${this.selectedFile.name}`;
    }
  }

  uploadFile() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.isUploading = true;
    this.message = 'Processing document...';

    this.http.post('http://localhost:8000/ingest', formData)
      .subscribe({
        next: () => {
          this.message = '✅ Document indexed successfully';
          this.isUploading = false;
          this.isIngested = true;
          this.cd.detectChanges();
        },
        error: () => {
          this.message = '❌ Upload failed';
          this.isUploading = false;
          this.cd.detectChanges();
        }
      });
  }

  getAnswer() {
    if (!this.question) return;

    this.answer = '';
    this.isQuerying = true;

    this.http.post('http://localhost:8000/query', {
      question: this.question
    }).subscribe({
      next: (res: any) => {
        this.answer = res.answer || 'No answer found';
        this.isQuerying = false;
        this.cd.detectChanges();
      },
      error: () => {
        this.answer = 'Error fetching answer';
        this.isQuerying = false;
      }
    });
  }
}