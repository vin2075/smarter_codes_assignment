# HTML DOM Search Application

A full-stack semantic search application that allows users to search through HTML content from any website using natural language queries. The application fetches web pages, chunks the content intelligently, and performs semantic search using vector embeddings stored in Weaviate.

## 🎯 Features

- **Semantic Search**: Natural language search using custom transformer-based embeddings
- **Smart HTML Chunking**: Intelligent content splitting while preserving HTML structure
- **Custom Vectorization**: Uses sentence-transformers model with PyTorch for local embedding generation
- **Vector Database**: Weaviate for efficient similarity search with custom vectors
- **Dual View Modes**: Toggle between rendered HTML and plain text views
- **Relevance Scoring**: Results ranked by semantic similarity (cosine distance)
- **Real-time Search**: Fast search across indexed content
- **URL Management**: Clear data per URL or entire database

## 🏗️ Architecture

### Frontend
- **Framework**: React.js
- **Styling**: Custom CSS
- **HTTP Client**: Axios
- **Features**: 
  - Dual view modes (HTML/Text)
  - Real-time loading states
  - Error handling
  - Responsive design

### Backend
- **Framework**: FastAPI (Python)
- **Web Scraping**: BeautifulSoup4
- **Embedding Model**: 
  - sentence-transformers/all-MiniLM-L6-v2 (Local)
  - Custom vectorization with PyTorch
- **Vector Database**: Weaviate 1.21.5
- **Server**: Uvicorn

### Vector Database
- **Database**: Weaviate (Open-source vector database)
- **Vectorizer**: None (Custom external vectorization)
- **Deployment**: Docker container
- **Features**:
  - Semantic search with vector similarity
  - Custom vector embedding integration
  - Efficient indexing and retrieval
  - Persistent storage

## 🛠️ Tech Stack

### Backend Dependencies
```
fastapi==0.107.0
uvicorn[standard]==0.23.2
requests==2.31.0
beautifulsoup4==4.12.2
transformers==4.42.0
sentence-transformers==2.2.2
torch==2.1.0
weaviate-client==3.22.0
python-dotenv==1.0.0
nltk==3.8.1
python-multipart==0.0.6
pydantic>=2.5.0,<3.0.0
```

### Frontend Dependencies
```
react
axios
```

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** and npm - [Download](https://nodejs.org/)
- **Docker** and Docker Compose - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/downloads)

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-name>
```

### 2. Backend Setup

#### Option A: Using Docker (Recommended)

1. **Start all services** (Weaviate + Backend):
```bash
docker-compose up --build
```

This will:
- Start Weaviate on `http://localhost:8080`
- Start Backend API on `http://localhost:8000`
- Download ML models automatically
- Create persistent volumes for data

2. **Verify services are running**:
```bash
# Check Weaviate health
curl http://localhost:8080/v1/.well-known/ready

# Check Backend health
curl http://localhost:8000/health
```

#### Option B: Manual Setup (Without Docker)

1. **Install Weaviate separately**:
```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=20 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
  -e DEFAULT_VECTORIZER_MODULE=none \
  semitechnologies/weaviate:1.21.5
```

2. **Install Python dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

3. **Set environment variables** (create `.env` file):
```bash
WEAVIATE_URL=http://localhost:8080
```

4. **Run the backend**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Start the development server**:
```bash
npm start
```

The frontend will open at `http://localhost:3000`

## 🎮 Usage

### Basic Search Flow

1. **Open the application** in your browser at `http://localhost:3000`

2. **Enter a website URL**:
   - You can enter with or without `https://` (e.g., `github.com` or `https://github.com`)
   - Press Enter or click "Search"

3. **Enter a search query**:
   - Use natural language (e.g., "machine learning tutorials")
   - The system will find semantically similar content

4. **View results**:
   - Toggle between HTML and Text view
   - See relevance scores (0-100%)
   - View token counts and source URLs

### API Endpoints

#### POST `/search`
Search for content in a website
```json
{
  "url": "https://example.com",
  "query": "search term"
}
```

#### DELETE `/clear`
Clear entire database
```bash
curl -X DELETE http://localhost:8000/clear
```

#### DELETE `/clear-url`
Clear data for specific URL
```json
{
  "url": "https://example.com"
}
```

#### GET `/health`
Check service health
```bash
curl http://localhost:8000/health
```

#### GET `/stats`
Get database statistics
```bash
curl http://localhost:8000/stats
```

## 🔧 Configuration

### Backend Configuration

Edit `docker-compose.yml` to modify:
- **Weaviate port**: Change `8080:8080`
- **Backend port**: Change `8000:8000`
- **Vector limits**: Modify `QUERY_DEFAULTS_LIMIT`

### Frontend Configuration

Edit `src/api.js` to change backend URL:
```javascript
const API = axios.create({
  baseURL: "http://localhost:8000", // Change this
});
```

### Model Configuration

The application uses a local transformer model for generating embeddings. To use a different embedding model, edit `main.py`:

```python
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # Change this to any sentence-transformers model
```

**Note**: Weaviate is configured with `DEFAULT_VECTORIZER_MODULE: none`, meaning:
- Embeddings are generated **externally** in the FastAPI backend
- Custom vectors are passed to Weaviate during indexing
- This approach gives full control over the embedding process
- No need for Weaviate's built-in vectorizers (text2vec-transformers, text2vec-openai, etc.)

## 🧪 Testing the Application

### Test with sample URLs:

```bash
# Example 1: Search Wikipedia
URL: https://en.wikipedia.org/wiki/Artificial_intelligence
Query: "neural networks"

# Example 2: Search documentation
URL: https://docs.python.org
Query: "list comprehension"

# Example 3: Search news
URL: https://news.ycombinator.com
Query: "startup funding"
```

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── logging_config.py
│   │   ├── schemas.py
│   │   ├── utils.py
│   │   └── weaviate_client.py
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   └── SearchForm.js
│   │   ├── api.js
│   │   ├── App.js
│   │   ├── styles.css
│   │   └── index.js
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🐛 Troubleshooting

### Issue: Backend can't connect to Weaviate
**Solution**: Ensure Weaviate is running
```bash
docker ps | grep weaviate
```

### Issue: "403 Forbidden" when fetching URLs
**Solution**: Some websites block automated requests. The app tries multiple user agents, but some sites may still block.

### Issue: No chunks found
**Solution**: The website might be JavaScript-heavy or block scraping. Try a different URL.

### Issue: Port already in use
**Solution**: 
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Issue: Docker containers won't start
**Solution**:
```bash
# Clean up Docker
docker-compose down -v
docker system prune -a
docker-compose up --build
```

## 📊 Performance Notes

- **First search on a URL**: Takes longer (fetching + indexing)
- **Subsequent searches**: Much faster (uses cached vectors)
- **Large pages**: May take 10-30 seconds for initial indexing
- **Model loading**: ~2-3 seconds on startup

## 🔒 Security Considerations

- The application is designed for local/development use
- Add authentication for production deployment
- Implement rate limiting for production
- Use environment variables for sensitive data
- Consider CORS settings for production

## 🚀 Production Deployment

### Additional steps for production:

1. **Set up proper environment variables**
2. **Use production-grade WSGI server** (e.g., Gunicorn)
3. **Enable HTTPS** with SSL certificates
4. **Set up proper CORS policies**
5. **Add authentication and rate limiting**
6. **Use managed Weaviate instance** or persistent volumes
7. **Build optimized frontend**: `npm run build`

## 📝 License

This project is for educational and demonstration purposes.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review Weaviate documentation: https://weaviate.io/developers/weaviate

## 🙏 Acknowledgments

- **Weaviate** - Vector database
- **FastAPI** - Backend framework
- **React** - Frontend framework

---

**Happy Searching! 🔍**
