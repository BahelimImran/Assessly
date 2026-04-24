import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';

interface QA  {
  question : string,
  isQuerying : boolean,
  answer:string
};
@Component({
  selector: 'app-upload-syllabus',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './upload-syllabus.component.html',
  styleUrls: ['./upload-syllabus.component.css']
})

export class UploadSyllabusComponent implements OnInit{

  apiBaseUrl = environment.apiBaseUrl;

  selectedFile: File | null = null;
  message = '';
  pickedFile : string ='';
  isUploading = false;

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

  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  ngOnInit(): void {
    console.log(this.listOfQA)

  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.pickedFile = `Selected: ${this.selectedFile.name}`;
    }
  }

  uploadFile() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.isUploading = true;
    this.message = 'Processing document...';

    this.http.post(`${this.apiBaseUrl}/ingest`, formData)
      .subscribe({
        next: () => {
          // this.message = '✅ Document indexed successfully';
          this.isUploading = false;
          this.isIngested = true;
          
      // ✅ Start listening to logs
          this.startLogStream();          
          this.cd.detectChanges();
        },
        error: () => {
          this.message = '❌ Upload failed';
          this.isUploading = false;
          this.cd.detectChanges();
        }
      });
  }
  startLogStream() {
    const eventSource = new EventSource(`${this.apiBaseUrl}/ingest/stream`);

    eventSource.onmessage = (event) => {
      console.log(event.data);

      // store logs in array (for UI)
      this.logs.push(event.data);

      // update message with latest log
      this.message = event.data;

      this.cd.detectChanges();
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };
  }


  getAnswer() {
    if (!this.question) return;

    this.answer = '';
    this.isQuerying = true;
    this.askDisable = true;
      this.listOfQA.push({
        "question": this.question,
        "isQuerying" : true,
        "answer": this.answer
      });


    this.http.post(`${this.apiBaseUrl}/query`, {
      question: this.question
    }).subscribe({
      next: (res: any) => {
        this.answer = res.answer || 'No answer found';
        
        // this.isQuerying = false;
        this.listOfQA[this.listOfQA.length-1].answer = this.answer;
        this.listOfQA[this.listOfQA.length-1].isQuerying = false;
        this.askDisable = false;
        this.cd.detectChanges();
      },
      error: () => {
        this.answer = 'Error fetching answer';
        // this.isQuerying = false;
        this.listOfQA[this.listOfQA.length-1].answer = this.answer;
        this.listOfQA[this.listOfQA.length-1].isQuerying = false;
        this.askDisable = false;
        this.cd.detectChanges();
      }
    });
  }
}

