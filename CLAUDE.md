# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Smart Vocab (智能词汇锻造场)** is a SaaS platform for vocabulary learning that:
- Automatically extracts vocabulary from PDF documents using OCR
- Generates structured question banks with AI-enhanced content
- Provides personalized training based on spaced repetition (SuperMemo-2 algorithm)

## Architecture

The system follows a **Modular Monolith** approach with clear module boundaries:

### Core Modules
- **Authentication Module**: JWT-based user authentication
- **Study Core**: Implements SM-2 (SuperMemo-2) spaced repetition algorithm
- **Data Management**: Handles vocabulary database and user progress
- **ETL & AI Pipeline** (async tasks):
  - PDF/OCR Parser (PaddleOCR)
  - Data Cleaning (LLM-based)
  - AI Enrichment Engine (generates example sentences and mnemonics)

### Technology Stack
- **Backend**: FastAPI (async Python web framework)
- **Database**: PostgreSQL with JSONB support for flexible vocabulary data
- **ORM**: SQLAlchemy (async mode)
- **Task Queue**: Celery + Redis for async PDF processing and AI enrichment
- **OCR**: PaddleOCR for Chinese/English text recognition
- **AI**: OpenAI/DeepSeek API for data cleaning and content generation
- **Frontend**: Vue 3 + TypeScript + Naive UI
- **Storage**: MinIO/S3 for PDF file storage

## Database Schema

### Key Tables

**users**: User authentication and subscription management
- Supports roles: `user`, `admin`
- Subscription tiers: `free`, `premium`, `enterprise`

**books**: Source vocabulary books (PDF documents)
- Tracks processing status: `processing`, `ready`, `failed`
- Stores metadata: title, file_url, total_pages, total_words

**words**: Shared vocabulary database (core asset)
- `definitions` (JSONB): Multi-part-of-speech definitions
  ```json
  [
    {"pos": "vt", "cn": "装饰; 点缀", "en": "make something look more attractive"},
    {"pos": "n", "cn": "勋章", "en": "medal"}
  ]
  ```
- `sentences` (JSONB): Bilingual example sentences
  ```json
  [
    {"en": "They decorated the room with flowers.", "cn": "他们用花装饰了房间。"}
  ]
  ```
- `mnemonic` (TEXT): Memory techniques and mnemonics
- `tags` (JSONB): Categorization tags (e.g., ["cet4", "business"])

**user_progress**: Individual learning progress (data isolation per user)
- Implements SM-2 algorithm fields:
  - `status`: 0=未学, 1=学习中, 2=复习中, 3=已掌握
  - `next_review_at`: Calculated next review time
  - `ease_factor`: SM-2 difficulty factor (default 2.5)
  - `interval`: Current review interval in days
  - `history` (JSONB): Review history for analytics

## Core Algorithms

### SuperMemo-2 (SM-2) Review Algorithm

User feedback ratings:
- 0 (Again): Completely forgot
- 3 (Hard): Vague memory
- 4 (Good): Recognized but slow
- 5 (Easy): Instant recall

Algorithm logic (Python pseudocode):
```python
def calculate_next_review(quality, prev_interval, prev_ease_factor):
    if quality < 3:
        # Failed to recall, reset progress
        return 1, prev_ease_factor  # Review in 1 day

    # Calculate new ease factor
    new_ef = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)  # Set lower bound

    # Calculate new interval
    if prev_interval == 0:
        new_interval = 1
    elif prev_interval == 1:
        new_interval = 6
    else:
        new_interval = int(prev_interval * new_ef)

    return new_interval, new_ef
```

## ETL Pipeline Workflow

1. **Upload & Slice**: Admin uploads PDF, backend converts pages to high-res images using `pdf2image`
2. **OCR Recognition**: PaddleOCR extracts text blocks with coordinate information
3. **Structured Cleaning (LLM Agent)**:
   - Send OCR output to LLM (GPT-3.5/4o-mini or DeepSeek)
   - Prompt: "Extract word information from this OCR text. Output as JSON with word, phonetic, definition fields."
4. **AI Enrichment**:
   - If PDF lacks example sentences or mnemonics, trigger enrichment
   - Prompt: "Generate 2 bilingual example sentences for word 'X' at college level, and provide a clever mnemonic using root/affix or association method."
5. **Database Insert**: Store cleaned base data + AI-generated enriched data in `words` table

## API Endpoints

### Study Endpoints
- `GET /api/study/session`: Get today's review + new words (e.g., 20 words)
  - Returns words with phonetics, definitions, example sentences, and mnemonics
  - Logic: Query `user_progress` where `next_review_at <= now()`, supplement with new words if needed
- `POST /api/study/submit`: Submit learning result for a word
  - Parameters: `{"word_id": 101, "quality": 4}` (0-5 rating)
  - Runs SM-2 algorithm and updates `next_review_at`

### Admin Endpoints
- `POST /api/admin/upload-pdf`: Upload file, returns `task_id`
- `GET /api/admin/task/{task_id}/status`: Poll parsing progress (OCR is slow, needs progress bar)

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source .venv/bin/activate

# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt
```

### Database Setup
```bash
# Start PostgreSQL with Docker
docker run -d --name smart-vocab-db \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=smart_vocab \
  -p 5432:5432 postgres:15

# Start Redis with Docker
docker run -d --name smart-vocab-redis \
  -p 6379:6379 redis:7
```

### Running the Application
```bash
# Run FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker for async tasks
celery -A app.tasks worker --loglevel=info

# Run Celery beat for scheduled tasks
celery -A app.tasks beat --loglevel=info
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_study.py

# Run with coverage
pytest --cov=app tests/
```

## Development Phases

### Phase 1: MVP - OCR Validation
- Create standalone Python script to test OCR pipeline
- Input: Local image file
- Process: PaddleOCR extraction + regex/OpenAI API for JSON extraction
- Output: Console print
- Goal: Validate data quality from scanned documents

### Phase 2: Backend & Database Foundation
- Set up FastAPI project structure
- Deploy PostgreSQL with Docker
- Define SQLAlchemy models (Word, User, Book, UserProgress)
- Implement registration/login endpoints with JWT

### Phase 3: Core Business Logic
- Implement "Upload PDF -> Async database insertion" workflow
- Implement "Get words -> Submit rating" workflow with SM-2 algorithm

### Phase 4: Frontend & Visualization
- Set up Vue 3 project
- Create word card component (flip animation, shows examples and mnemonics)
- Build study session interface with rating buttons

## Important Notes

### JSONB Usage
PostgreSQL's JSONB type is critical for this project:
- Stores variable-length data (multiple definitions, example sentences)
- Allows flexible querying without schema changes
- Use SQLAlchemy's `JSONB` type for these fields

### Async Processing
- PDF parsing and AI enrichment are time-consuming operations
- Must use Celery for async processing to avoid blocking main thread
- Provide progress tracking for long-running tasks

### AI Integration
- Use prompt engineering for data cleaning and content generation
- Keep prompts consistent for quality control
- Consider rate limiting and cost management for API calls

### Security Considerations
- Hash passwords with bcrypt
- Use JWT tokens with appropriate expiration
- Validate and sanitize all user inputs
- Implement rate limiting on API endpoints
- Secure file upload validation (file type, size limits)
