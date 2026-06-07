import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';

interface QA  {
  question : string,
  isQuerying : boolean,
  answer:string,
  queryJobId?: string,
  status?: string
};

interface AuthUser {
  user_id: string;
  username: string;
  role: string;
  email?: string | null;
}

interface StreamTokenResponse {
  stream_token: string;
}

const ACCESS_TOKEN_STORAGE_KEY = 'assessly_access_token';
@Component({
  selector: 'app-upload-syllabus',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './upload-syllabus.component.html',
  styleUrls: ['./upload-syllabus.component.css']
})

export class UploadSyllabusComponent implements OnInit{

  apiBaseUrl = environment.apiBaseUrl;

  activeUserId: string = '';
  userId = '';
  accessToken = sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || '';
  authUser: AuthUser | null = null;
  authMode: 'login' | 'register' = 'login';
  authUsername = '';
  authEmail = '';
  authPassword = '';
  authMessage = '';

  selectedFile: File | null = null;
  message = '';
  pickedFile : string ='';
  isUploading = false;
  duplicatePending = false;

  question: string = '';
  answer: string = '';
  isIngested: boolean = false;
  isQuerying: boolean = false;
  askDisable: boolean = false;

  listOfQA : QA[] = [];
  logs: string[] = [];

  ragConfig = [
  {
    title: 'Chunking',
    value: 'Custom semantic + title-based chunking'
  },
  {
    title: 'Embeddings',
    value: 'bge-m3'
  },
  {
    title: 'Vector DB',
    value: 'Qdrant'
  },
  {
    title: 'LLM',
    value: 'Ollama (qwen2.5:7b)'
  }
];

showInfo: boolean = false;

demoInfo = {
  mode: 'Demo Mode',
  description: 'This application demonstrates a production-style RAG pipeline with real-time ingestion and querying.',
  infra: [
    'FastAPI backend with Redis-backed workers',
    'Angular SPA frontend',
    'Qdrant vector database with PostgreSQL metadata'
  ],
  limitations: [
    'Demo mode uses seeded/demo documents only',
    'Local model latency depends on the configured Ollama server'
  ],
  strengths: [
    'Real-time document ingestion',
    'Semantic search with embeddings',
    'Grounded LLM responses (no hallucination)'
  ]
};

showRagInfo: boolean = false;

ragArchitecture = {
  pipeline: [
    'Document Upload',
    'PDF Parsing (Docling)',
    'Semantic Chunking',
    'Embedding Generation',
    'Vector Storage (Qdrant)',
    'Query Embedding',
    'Similarity Search',
    'Context Injection',
    'LLM Response Generation'
  ],
  components: [
    {
      title: 'Chunking',
      value: `Docling-based parsing with parent and child chunk creation.
Optimized to preserve document structure and context continuity.`
    },
    {
      title: 'Embeddings',
      value: `bge-m3 via Ollama
High-quality dense vector embeddings optimized for semantic search.`
    },
    {
      title: 'Vector DB',
      value: `Qdrant with dense, sparse, and metadata-filtered retrieval
Supports efficient similarity search and document-level traceability.`
    },
    {
      title: 'Retrieval',
      value: `Hybrid dense + sparse retrieval with user and document filters
Context ranking tuned for relevance and minimal hallucination.`
    },
    {
      title: 'LLM Generation',
      value: 'Ollama qwen2.5:7b for grounded answers'
    },
    {
      title: 'Orchestration',
      value: `FastAPI, Redis Streams, and background workers for ingestion and query jobs.`
    },
    // {
    //   title: 'Design Philosophy',
    //   value: `Built for scalable semantic retrieval, low-latency inference, and explainable AI responses.`
    // }
  ]
};
  files: any;
  ingestionProcessing: boolean = false;



  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.refreshSession();
  }

  get isAuthenticated(): boolean {
    return !!this.accessToken && !!this.authUser;
  }

  get isGuestMode(): boolean {
    return this.authUser?.role === 'guest';
  }

  get canUpload(): boolean {
    return this.isAuthenticated && !this.isGuestMode;
  }

  private authHeaders(): HttpHeaders {
    return new HttpHeaders({
      Authorization: `Bearer ${this.accessToken}`
    });
  }

  private applyAuthResponse(res: any): void {
    this.accessToken = res?.access_token || '';
    this.authUser = res?.user || null;
    this.activeUserId = this.authUser?.user_id || '';

    if (this.accessToken) {
      sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, this.accessToken);
    }

    this.getKnowledgeBaseFile();
  }

  refreshSession(): void {
    this.http.post(`${this.apiBaseUrl}/auth/refresh`, {}, { withCredentials: true })
      .subscribe({
        next: (res: any) => {
          this.applyAuthResponse(res);
          this.cd.detectChanges();
        },
        error: () => {
          sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
          this.accessToken = '';
          this.authUser = null;
          this.activeUserId = '';
          this.files = [];
          this.cd.detectChanges();
        }
      });
  }

  login(): void {
    this.authMessage = '';
    this.http.post(`${this.apiBaseUrl}/auth/login`, {
      username: this.authUsername,
      password: this.authPassword
    }, { withCredentials: true }).subscribe({
      next: (res: any) => {
        this.applyAuthResponse(res);
        this.authPassword = '';
        this.cd.detectChanges();
      },
      error: (err) => {
        this.authMessage = err?.error?.detail || 'Login failed';
        this.cd.detectChanges();
      }
    });
  }

  register(): void {
    this.authMessage = '';
    this.http.post(`${this.apiBaseUrl}/auth/register`, {
      username: this.authUsername,
      email: this.authEmail || null,
      password: this.authPassword
    }, { withCredentials: true }).subscribe({
      next: (res: any) => {
        this.applyAuthResponse(res);
        this.authPassword = '';
        this.cd.detectChanges();
      },
      error: (err) => {
        this.authMessage = err?.error?.detail || 'Registration failed';
        this.cd.detectChanges();
      }
    });
  }

  continueAsGuest(): void {
    this.authMessage = '';
    this.http.post(`${this.apiBaseUrl}/auth/guest`, {}, { withCredentials: true }).subscribe({
      next: (res: any) => {
        this.applyAuthResponse(res);
        this.cd.detectChanges();
      },
      error: (err) => {
        this.authMessage = err?.error?.detail || 'Guest mode failed';
        this.cd.detectChanges();
      }
    });
  }

  logout(): void {
    this.http.post(`${this.apiBaseUrl}/auth/logout`, {}, { withCredentials: true }).subscribe({
      next: () => this.clearSession(),
      error: () => this.clearSession()
    });
  }

  clearSession(): void {
    sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    this.accessToken = '';
    this.authUser = null;
    this.activeUserId = '';
    this.files = [];
    this.logs.length = 0;
    this.message = '';
    this.cd.detectChanges();
  }

  private handleProtectedApiError(err: any, fallbackMessage: string): string {
    if (err?.status === 401) {
      this.clearSession();
      this.authMessage = 'Session expired. Please login again.';
      return this.authMessage;
    }

    if (err?.status === 403) {
      return err?.error?.detail || 'You do not have permission for this action.';
    }

    return err?.error?.detail || fallbackMessage;
  }

  saveUserId(): void {
  const cleanUserId = this.userId.trim();

  if (!cleanUserId) return;
  this.activeUserId = cleanUserId;
  this.getKnowledgeBaseFile();
}

  getKnowledgeBaseFile(){
    if (!this.accessToken) return;

    this.http.get(`${this.apiBaseUrl}/knowledge-base/files?tenant_id=default_tenant`, {
      headers: this.authHeaders()
    })
      .subscribe({
        next: (res:any) => {
          this.files = res.files;     
          this.cd.detectChanges();
        },
        error: (err) => {
          this.message = this.handleProtectedApiError(err, 'Knowledge base not found');
          // this.isUploading = false;
          this.cd.detectChanges();
        }
      });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.pickedFile = `Selected: ${this.selectedFile.name}`;
      this.duplicatePending = false;
      this.message = '';
      this.logs.length = 0;
    }
  }

  uploadFile(replaceExisting = false) {
    if (!this.selectedFile || !this.canUpload) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);
    formData.append('replace_existing', String(replaceExisting));

    this.logs.length = 0;
    this.ingestionProcessing = true;
    this.isUploading = true;
    this.duplicatePending = false;
    this.message = replaceExisting ? 'Replacing document safely...' : 'Processing document...';

    this.http.post(`${this.apiBaseUrl}/ingest`, formData, {
      headers: this.authHeaders()
    })
      .subscribe({
        next: (ingestRes:any) => {
          this.message = ingestRes?.message || '';
          this.isUploading = false;

          if (ingestRes?.status === 'duplicate') {
            this.duplicatePending = true;
            this.isIngested = false;
            this.cd.detectChanges();
            return;
          }

          this.isIngested = true;
          // this.activeUserId = ingestRes['user_id'];
          
          
      // ✅ Start listening to logs
          if (ingestRes?.job_id) {
            this.startLogStream(ingestRes.job_id);
          }
          this.cd.detectChanges();
        },
        error: (err) => {
          this.message = this.handleProtectedApiError(err, 'Upload failed');
          this.isUploading = false;
          this.duplicatePending = false;
          this.cd.detectChanges();
        }
      });
  }
  confirmReplacement() {
    if (!this.duplicatePending || this.isUploading) return;

    this.duplicatePending = false;
    this.uploadFile(true);
  }

  startLogStream(job_id:string) {
    this.http.post<StreamTokenResponse>(`${this.apiBaseUrl}/ingest/jobs/${job_id}/stream-token`, {}, {
      headers: this.authHeaders()
    }).subscribe({
      next: (res) => {
        const streamToken = encodeURIComponent(res.stream_token);
        const eventSource = new EventSource(`${this.apiBaseUrl}/ingest/stream/${job_id}?stream_token=${streamToken}`);

        eventSource.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          const logMessage = payload.message || '';

          this.logs.push(logMessage);
          this.message = logMessage;

          if (logMessage.includes('All set')) {
            this.ingestionProcessing = false;
            this.getKnowledgeBaseFile();
          }

          this.cd.detectChanges();
        };

        eventSource.onerror = () => {
          eventSource.close();
        };
      },
      error: (err) => {
        this.message = this.handleProtectedApiError(err, 'Could not start ingestion stream');
        this.ingestionProcessing = false;
        this.cd.detectChanges();
      }
    });
  }

  getAnswer() {
    if (!this.question || !this.isAuthenticated) return;

    this.answer = '';
    this.isQuerying = true;
    this.askDisable = true;
      this.listOfQA.push({
        "question": this.question,
        "isQuerying" : true,
        "answer": this.answer,
        "status": "queued"
      });

    this.http.post(`${this.apiBaseUrl}/query`, {
      question: this.question
    }, {
      headers: this.authHeaders()
    }).subscribe({
      next: (res: any) => {
        const currentQA = this.listOfQA[this.listOfQA.length - 1];
        currentQA.queryJobId = res.query_job_id;
        currentQA.status = res.status || 'queued';
        currentQA.answer = 'Thinking...';
        this.startQueryStream(res.query_job_id, this.listOfQA.length - 1);
        this.cd.detectChanges();
      },
      error: (err) => {
        this.answer = this.handleProtectedApiError(err, 'Error fetching answer');
        // this.isQuerying = false;
        this.listOfQA[this.listOfQA.length-1].answer = this.answer;
        this.listOfQA[this.listOfQA.length-1].isQuerying = false;
        this.askDisable = false;
        this.cd.detectChanges();
      }
    });
  }

  startQueryStream(queryJobId: string, qaIndex: number) {
    this.http.post<StreamTokenResponse>(`${this.apiBaseUrl}/query/jobs/${queryJobId}/stream-token`, {}, {
      headers: this.authHeaders()
    }).subscribe({
      next: (res) => {
        const streamToken = encodeURIComponent(res.stream_token);
        const eventSource = new EventSource(`${this.apiBaseUrl}/query/jobs/${queryJobId}/stream?stream_token=${streamToken}`);

        eventSource.onmessage = (event) => {
          if (event.data && event.data !== '{}') {
            const payload = JSON.parse(event.data);
            const qa = this.listOfQA[qaIndex];
            qa.status = payload.status;
            qa.answer = payload.message;
          }

          this.getQueryJobStatus(queryJobId, qaIndex, eventSource);
          this.cd.detectChanges();
        };

        eventSource.onerror = () => {
          eventSource.close();
          this.getQueryJobStatus(queryJobId, qaIndex);
        };
      },
      error: (err) => {
        const qa = this.listOfQA[qaIndex];
        qa.answer = this.handleProtectedApiError(err, 'Could not start query stream');
        qa.isQuerying = false;
        this.askDisable = false;
        this.cd.detectChanges();
      }
    });
  }
  getQueryJobStatus(queryJobId: string, qaIndex: number, eventSource?: EventSource) {
    this.http.get(`${this.apiBaseUrl}/query/jobs/${queryJobId}`, {
      headers: this.authHeaders()
    }).subscribe({
      next: (job: any) => {
        const qa = this.listOfQA[qaIndex];
        qa.status = job.status;

        if (job.status === 'completed') {
          qa.answer = job.answer || 'No answer found';
          qa.isQuerying = false;
          this.askDisable = false;
          eventSource?.close();
        }

        if (job.status === 'failed') {
          qa.answer = job.error || 'Query failed';
          qa.isQuerying = false;
          this.askDisable = false;
          eventSource?.close();
        }

        this.cd.detectChanges();
      },
      error: (err) => {
        const qa = this.listOfQA[qaIndex];
        qa.answer = this.handleProtectedApiError(err, 'Error fetching query status');
        qa.isQuerying = false;
        this.askDisable = false;
        eventSource?.close();
        this.cd.detectChanges();
      }
    });
  }
}
