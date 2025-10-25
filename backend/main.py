from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
import requests, hashlib, logging
import weaviate
from transformers import AutoTokenizer, AutoModel
import torch
from typing import List, Dict, Any, Optional
import os
import uuid
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global variables for model
tokenizer = None
model = None
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global tokenizer, model, client
    
    # Load model and tokenizer
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    
    # Initialize Weaviate client
    if os.getenv("RUNNING_IN_DOCKER"):
        WEAVIATE_URL = "http://weaviate:8080"
    else:
        WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    
    client = weaviate.Client(url=WEAVIATE_URL)
    logger.info(f"🔗 Connected to Weaviate at {WEAVIATE_URL}")
    
    # Ensure schema exists
    ensure_schema()
    
    yield
    
    # Shutdown (cleanup if needed)
    pass

app = FastAPI(lifespan=lifespan)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_url(url: str) -> str:
    """Validate and fix URL by adding scheme if missing"""
    url = url.strip()
    
    # Check if URL has a scheme
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        logger.info(f"Added scheme to URL: {url}")
    
    # Validate the URL has both scheme and netloc
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL format: {url}")
    
    return url

def get_embedding(text: str) -> List[float]:
    """Generate embedding vector for text"""
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        truncation=True, 
        max_length=512, 
        padding=True,
        return_attention_mask=True
    )
    with torch.no_grad():
        outputs = model(**inputs)
    
    attention_mask = inputs['attention_mask']
    embeddings = outputs.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
    sum_embeddings = torch.sum(embeddings * mask_expanded, 1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    embeddings = sum_embeddings / sum_mask
    return embeddings[0].tolist()

def get_html_chunks(url: str) -> List[Dict]:
    """Fetch HTML and chunk it while preserving structure"""
    url = validate_url(url)
    
    # Try with multiple user agents and headers
    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    ]
    
    html_content = None
    last_error = None
    
    for headers in headers_list:
        try:
            res = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
            res.raise_for_status()
            html_content = res.text
            logger.info(f"✅ Successfully fetched {len(html_content)} bytes from {url}")
            break
        except requests.exceptions.HTTPError as e:
            last_error = e
            logger.warning(f"HTTP Error {e.response.status_code}: {str(e)}")
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden - Site may be blocking automated requests")
            continue
        except Exception as e:
            last_error = e
            logger.warning(f"Request failed: {str(e)}")
            continue
    
    if not html_content:
        raise Exception(f"Failed to fetch URL after multiple attempts. Last error: {str(last_error)}")
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script, style, noscript tags
    for tag in soup(["script", "style", "noscript", "meta", "link"]):
        tag.extract()
    
    chunks = []
    seen_text = set()  # Track unique text to avoid duplicates
    
    # Process each major HTML element
    elements = soup.find_all(['div', 'section', 'article', 'header', 'footer', 
                              'nav', 'main', 'aside', 'p', 'h1', 'h2', 'h3', 
                              'h4', 'h5', 'h6', 'ul', 'ol', 'table', 'li', 'span'])
    
    logger.info(f"Found {len(elements)} HTML elements to process")
    
    for element in elements:
        html_str = str(element)
        text_content = element.get_text(separator=" ", strip=True)
        
        # Skip empty or very short elements
        if not text_content or len(text_content) < 15:
            continue
        
        # Skip duplicates
        text_hash = hashlib.md5(text_content.encode()).hexdigest()
        if text_hash in seen_text:
            continue
        seen_text.add(text_hash)
        
        # Check token count
        try:
            token_count = len(tokenizer.encode(text_content, add_special_tokens=False))
        except Exception as e:
            logger.warning(f"Token encoding error: {str(e)}")
            continue
        
        # If element is too large, try to split it
        if token_count > 500:
            sub_elements = element.find_all(['p', 'li', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=False)
            if sub_elements:
                for sub_elem in sub_elements:
                    sub_html = str(sub_elem)
                    sub_text = sub_elem.get_text(separator=" ", strip=True)
                    if sub_text and len(sub_text) >= 15:
                        sub_hash = hashlib.md5(sub_text.encode()).hexdigest()
                        if sub_hash not in seen_text:
                            seen_text.add(sub_hash)
                            try:
                                sub_tokens = len(tokenizer.encode(sub_text, add_special_tokens=False))
                                if sub_tokens <= 500:
                                    chunks.append({
                                        'html': sub_html,
                                        'text': sub_text,
                                        'tokens': sub_tokens
                                    })
                            except Exception:
                                continue
            else:
                # Fallback: chunk the text
                text_chunks = chunk_text_content(text_content, max_tokens=500)
                for i, chunk_text in enumerate(text_chunks):
                    chunk_html = f'<div class="chunk-{i}">{chunk_text}</div>'
                    chunks.append({
                        'html': chunk_html,
                        'text': chunk_text,
                        'tokens': len(tokenizer.encode(chunk_text, add_special_tokens=False))
                    })
        else:
            chunks.append({
                'html': html_str,
                'text': text_content,
                'tokens': token_count
            })
    
    logger.info(f"Created {len(chunks)} unique chunks")
    
    # If no chunks found, try to get body text
    if len(chunks) == 0:
        body_text = soup.get_text(separator=" ", strip=True)
        logger.warning(f"No chunks found! Body text length: {len(body_text)}")
        logger.warning(f"First 500 chars: {body_text[:500]}")
        
        # Create at least one chunk from body if it has content
        if body_text and len(body_text) > 20:
            chunks.append({
                'html': f'<div>{body_text[:5000]}</div>',
                'text': body_text[:5000],
                'tokens': len(tokenizer.encode(body_text[:5000], add_special_tokens=False))
            })
    
    return chunks

def chunk_text_content(text: str, max_tokens: int = 500) -> List[str]:
    """Fallback text chunking for large text blocks"""
    try:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        for i in range(0, len(tokens), max_tokens):
            sub_tokens = tokens[i:i+max_tokens]
            chunk = tokenizer.decode(sub_tokens, skip_special_tokens=True)
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks
    except Exception as e:
        logger.error(f"Chunking error: {str(e)}")
        return []

def ensure_schema():
    """Ensure HtmlChunk schema exists"""
    schema_name = "HtmlChunk"
    
    try:
        if client.schema.exists(schema_name):
            logger.info(f"Schema {schema_name} already exists")
            return
        
        schema = {
            "class": schema_name,
            "vectorizer": "none",
            "properties": [
                {"name": "html", "dataType": ["text"]},
                {"name": "text", "dataType": ["text"]},
                {"name": "url", "dataType": ["string"]},
                {"name": "sha256", "dataType": ["string"]},
                {"name": "tokens", "dataType": ["int"]}
            ]
        }
        client.schema.create_class(schema)
        logger.info(f"✅ Created schema: {schema_name}")
    except Exception as e:
        logger.error(f"Schema creation error: {str(e)}")

@app.post("/search")
async def search(req: Request):
    try:
        data = await req.json()
        url = data.get("url")
        query = data.get("query")
        
        if not url or not query:
            raise HTTPException(status_code=400, detail="URL and query are required")
        
        # Validate URL format
        try:
            url = validate_url(url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        logger.info(f"🔍 Searching URL: {url}, Query: {query}")
        
        # Step 1: Fetch and chunk HTML
        try:
            chunks = get_html_chunks(url)
            logger.info(f"📦 Created {len(chunks)} HTML chunks")
            
            if len(chunks) == 0:
                return {
                    "results": [],
                    "total": 0,
                    "message": "No content could be extracted from the URL. The site may be blocking requests or has no text content.",
                    "url": url
                }
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to fetch URL: {str(e)}. The site may be blocking automated requests or requires authentication."
            )
        
        # Step 2: Deduplicate based on text content
        unique_chunks = {}
        for chunk in chunks:
            sha = hashlib.sha256(chunk['text'].encode("utf-8")).hexdigest()
            if sha not in unique_chunks:
                unique_chunks[sha] = chunk
        
        logger.info(f"✨ Unique chunks: {len(unique_chunks)}")
        
        # Step 3: Store new chunks
        schema_name = "HtmlChunk"
        stored_count = 0
        
        for sha, chunk in unique_chunks.items():
            # Check if chunk already exists
            result = client.query.get(schema_name, ["sha256"]).with_where({
                "path": ["sha256"],
                "operator": "Equal",
                "valueString": sha
            }).with_limit(1).do()
            
            existing = result.get("data", {}).get("Get", {}).get(schema_name, [])
            
            if not existing:
                embedding = get_embedding(chunk['text'])
                
                client.data_object.create(
                    data_object={
                        "html": chunk['html'],
                        "text": chunk['text'],
                        "url": url,
                        "sha256": sha,
                        "tokens": chunk['tokens']
                    },
                    class_name=schema_name,
                    vector=embedding,
                    uuid=str(uuid.uuid4())
                )
                stored_count += 1
        
        logger.info(f"💾 Stored {stored_count} new chunks")
        
        # Step 4: Search with URL filter
        query_embedding = get_embedding(query)
        
        search_result = (
            client.query
            .get(schema_name, ["html", "text", "url", "tokens"])
            .with_near_vector({"vector": query_embedding})
            .with_where({
                "path": ["url"],
                "operator": "Equal",
                "valueString": url
            })
            .with_limit(10)
            .with_additional(["distance"])
            .do()
        )
        
        hits = search_result.get("data", {}).get("Get", {}).get(schema_name, [])
        logger.info(f"🎯 Found {len(hits)} search results")
        
        # Format results
        results = []
        for hit in hits:
            results.append({
                "html": hit.get("html", ""),
                "text": hit.get("text", ""),
                "url": hit.get("url", ""),
                "tokens": hit.get("tokens", 0),
                "score": 1 - hit.get("_additional", {}).get("distance", 1)
            })
        
        return {"results": results, "total": len(results), "chunks_indexed": stored_count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in search endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
async def clear_database():
    """Clear all data from Weaviate"""
    try:
        schema_name = "HtmlChunk"
        if client.schema.exists(schema_name):
            client.schema.delete_class(schema_name)
            logger.info(f"🗑️ Deleted schema: {schema_name}")
        ensure_schema()
        return {"status": "cleared", "message": "Database cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear-url")
async def clear_url(req: Request):
    """Clear data for a specific URL"""
    try:
        data = await req.json()
        url = data.get("url")
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        url = validate_url(url)
        schema_name = "HtmlChunk"
        
        result = client.batch.delete_objects(
            class_name=schema_name,
            where={
                "path": ["url"],
                "operator": "Equal",
                "valueString": url
            }
        )
        
        deleted_count = result.get("results", {}).get("successful", 0)
        logger.info(f"🗑️ Deleted {deleted_count} chunks for URL: {url}")
        
        return {"status": "cleared", "url": url, "deleted": deleted_count}
    except Exception as e:
        logger.error(f"Error clearing URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    return {"status": "ok", "weaviate": weaviate_url}

@app.get("/stats")
async def stats():
    """Get database statistics"""
    try:
        schema_name = "HtmlChunk"
        result = client.query.aggregate(schema_name).with_meta_count().do()
        count = result.get("data", {}).get("Aggregate", {}).get(schema_name, [{}])[0].get("meta", {}).get("count", 0)
        return {"total_chunks": count}
    except Exception as e:
        return {"error": str(e)}