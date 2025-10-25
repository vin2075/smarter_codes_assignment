import React, { useState } from 'react';
import { searchHTML } from '../api';
import '../styles.css';

const SearchForm = () => {
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState('html'); // 'html' or 'text'

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults([]);

    try {
      const data = await searchHTML(url, query);
      if (data.results && data.results.length > 0) {
        setResults(data.results);
      } else {
        setError('No results found. Try a different query or URL.');
      }
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || 'Error fetching results';
      setError(`Error: ${errorMsg}. Please check your URL and backend connection.`);
    }
    setLoading(false);
  };

  return (
    <div className="app-container">
      <h1>HTML DOM Search</h1>
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder="Enter website URL (e.g., github.com or https://example.com)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Enter search query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {results.length > 0 && (
        <>
          <div className="results-info">
            <p>Found {results.length} matching chunk{results.length !== 1 ? 's' : ''}</p>
          </div>
          <div className="view-toggle">
            <button 
              className={viewMode === 'html' ? 'active' : ''}
              onClick={() => setViewMode('html')}
            >
              HTML View
            </button>
            <button 
              className={viewMode === 'text' ? 'active' : ''}
              onClick={() => setViewMode('text')}
            >
              Text View
            </button>
          </div>
        </>
      )}

      <div className="results-container">
        {results.map((res, i) => (
          <div key={i} className="result-card">
            <div className="result-header">
              <h3>Match #{i + 1}</h3>
              <small className={`score ${res.score >= 0.8 ? 'high' : res.score >= 0.5 ? 'medium' : 'low'}`}>Score: {(res.score * 100)?.toFixed(2)}%</small>
            </div>
            
            {viewMode === 'html' ? (
              <div className="html-content">
                <div 
                  className="rendered-html"
                  dangerouslySetInnerHTML={{ __html: res.html }}
                />
                <details className="html-code">
                  <summary>View HTML Source</summary>
                  <pre><code>{res.html}</code></pre>
                </details>
              </div>
            ) : (
              <div className="text-content">
                <p>{res.text}</p>
              </div>
            )}
            
            <div className="result-meta">
              <small>Tokens: {res.tokens}</small>
              <small>URL: {res.url}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchForm;