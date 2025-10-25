import os
import weaviate
from typing import List

# -------------------------------
# Configuration
# -------------------------------
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://host.docker.internal:8080')
CLASS_NAME = 'HtmlChunk'

client = weaviate.Client(url=WEAVIATE_URL)


# -------------------------------
# Ensure schema exists
# -------------------------------
def ensure_schema():
    schema = {
        'class': CLASS_NAME,
        'properties': [
            {'name': 'url', 'dataType': ['string']},
            {'name': 'html', 'dataType': ['text']},
            {'name': 'chunk_id', 'dataType': ['string']},
            {'name': 'tokens', 'dataType': ['int']},
            {'name': 'sha256', 'dataType': ['string']}
        ]
    }

    if not client.schema.contains({'class': CLASS_NAME}):
        client.schema.create_class(schema)


# -------------------------------
# Upsert chunks into Weaviate
# -------------------------------
def upsert_chunks(objects: List[dict]):
    """
    objects: List of dicts
    [{'id': uuid, 'vector': [...], 'properties': {...}}]
    """
    with client.batch as batch:
        batch.batch_size = 64
        for obj in objects:
            batch.add_data_object(
                obj['properties'],
                CLASS_NAME,
                uuid=obj['id'],
                vector=obj['vector']
            )


# -------------------------------
# Find existing chunk by SHA256
# -------------------------------
def find_by_sha(sha: str):
    """
    Query Weaviate for objects with a given sha256
    """
    where = {
        'path': ['sha256'],
        'operator': 'Equal',
        'valueString': sha
    }
    res = client.query.get(
        CLASS_NAME,
        ['chunk_id', 'sha256', 'url', 'html', 'tokens']
    ).with_where(where).do()

    hits = res.get('data', {}).get('Get', {}).get(CLASS_NAME, [])
    return hits


# -------------------------------
# Perform semantic search
# -------------------------------
def semantic_search(query_vector, top_k=10):
    """
    Perform semantic search in Weaviate using a query vector
    """
    near_vector = {'vector': query_vector}
    result = client.query.get(
        CLASS_NAME,
        ['url', 'html', 'chunk_id', 'tokens', 'sha256']
    ).with_near_vector(near_vector).with_limit(top_k).with_additional(['distance']).do()

    hits = result.get('data', {}).get('Get', {}).get(CLASS_NAME, [])
    return hits
