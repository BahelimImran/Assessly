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
  accessToken = localStorage.getItem('assessly_access_token') || '';
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
    value: 'Numic-embed-text'
  },
  {
    title: 'Vector DB',
    value: 'ChromaDB'
  },
  {
    title: 'LLM',
    value: 'Ollama (Mistral)'
  }
];

showInfo: boolean = false;

demoInfo = {
  mode: 'Demo Mode',
  description: 'This application demonstrates a production-style RAG pipeline with real-time ingestion and querying.',
  infra: [
    'Backend runs locally via secure tunnel (ngrok)',
    'Frontend hosted separately (Angular SPA)',
    'Vector DB persisted locally (ChromaDB)'
  ],
  limitations: [
    'Backend availability depends on local machine',
    'ngrok URL may change on restart'
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
    'PDF Parsing (unstructured)',
    'Semantic Chunking',
    'Embedding Generation',
    'Vector Storage (ChromaDB)',
    'Query Embedding',
    'Similarity Search',
    'Context Injection',
    'LLM Response Generation'
  ],
  components: [
    {
      title: '📄 Chunking',
      value: `Custom semantic + title-aware chunking using unstructured.partition.pdf
Optimized to preserve document structure and context continuity.`
    },
    {
      title: '🧠 Embeddings',
      value: `Nomic AI – nomic-embed-text (via Ollama)
High-quality dense vector embeddings optimized for semantic search.`
    },
    {
      title: '🗂 Vector DB',
      value: `ChromaDB with metadata filtering
Supports efficient similarity search and document-level traceability.`
    },
    {
      title: '🔍 Retrieval',
      value: `Top-K similarity search using cosine similarity
Context ranking tuned for relevance and minimal hallucination.`
    },
    {
      title: '🤖 LLM (Generation)',
      value: 'Ollama (Mistral) for grounded answers'
    },
    {
      title: '🧩 Orchestration',
      value: `LangChain-based pipeline for ingestion, retrieval, and response generation.`
    },
    // {
    //   title: '🚀 Design Philosophy',
    //   value: `Built for scalable semantic retrieval, low-latency inference, and explainable AI responses.`
    // }
  ]
};
  files: any;
  ingestionProcessing: boolean = false;



  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  ngOnInit(): void {
    console.log(this.listOfQA)
  // const savedUserId = localStorage.getItem('assessly_user_id');

  // if (savedUserId) {
  //   this.userId = savedUserId;
  //   this.activeUserId = savedUserId;
  // }

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
      localStorage.setItem('assessly_access_token', this.accessToken);
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
          localStorage.removeItem('assessly_access_token');
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
    localStorage.removeItem('assessly_access_token');
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

  // localStorage.setItem('assessly_user_id', cleanUserId);
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
    const token = encodeURIComponent(this.accessToken);
    const eventSource = new EventSource(`${this.apiBaseUrl}/ingest/stream/${job_id}?access_token=${token}`);

    eventSource.onmessage = (event) => {
      console.log(JSON.parse(event.data).message);

      // store logs in array (for UI)
      this.logs.push(JSON.parse(event.data).message);

      // update message with latest log
      this.message = JSON.parse(event.data).message;

      if(JSON.parse(event.data).message === "✅ All set! You can start asking questions now."){
        this.ingestionProcessing = false;
        this.getKnowledgeBaseFile();
      }

      this.cd.detectChanges();
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };
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
        currentQA.answer = '⏳ Thinking...';
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
    const token = encodeURIComponent(this.accessToken);
    const eventSource = new EventSource(`${this.apiBaseUrl}/query/jobs/${queryJobId}/stream?access_token=${token}`);

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
