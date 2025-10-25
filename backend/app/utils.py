import uuid

def split_into_chunks(sentences, max_tokens, num_tokens):
    """
    Splits a list of sentences into chunks with a maximum number of tokens.
    
    Args:
        sentences (list): List of sentences to split.
        max_tokens (int): Maximum tokens allowed per chunk.
        num_tokens (function): Function that returns the token count of a string.
        
    Returns:
        list: List of chunks, each chunk is a dict with chunk_id, text, tokens.
    """
    chunks = []
    current = ''
    current_tokens = 0

    for sent in sentences:
        tcount = num_tokens(sent)

        if tcount > max_tokens:
            # Naive split by words
            words = sent.split()
            piece = []
            for w in words:
                piece.append(w)
                ptext = ' '.join(piece)
                if num_tokens(ptext) >= max_tokens:
                    cid = str(uuid.uuid4())
                    chunks.append({
                        'chunk_id': cid,
                        'text': ptext,
                        'tokens': num_tokens(ptext)
                    })
                    piece = []
            # Add remaining words if any
            if piece:
                ptext = ' '.join(piece)
                cid = str(uuid.uuid4())
                chunks.append({
                    'chunk_id': cid,
                    'text': ptext,
                    'tokens': num_tokens(ptext)
                })
            continue

        # Combine sentences into a candidate chunk
        if current == '':
            candidate = sent
        else:
            candidate = current + ' ' + sent

        cand_tokens = num_tokens(candidate)
        if cand_tokens <= max_tokens:
            current = candidate
            current_tokens = cand_tokens
        else:
            if current:
                cid = str(uuid.uuid4())
                chunks.append({
                    'chunk_id': cid,
                    'text': current,
                    'tokens': current_tokens
                })
            current = sent
            current_tokens = tcount

    # Add any remaining text
    if current:
        cid = str(uuid.uuid4())
        chunks.append({
            'chunk_id': cid,
            'text': current,
            'tokens': current_tokens
        })

    return chunks
