import React, { useEffect, useState } from 'react';
import '../styles/Inbox.css';

interface Email {
  id: string;
  from: string;
  to: string;
  subject: string;
  snippet: string;
  date: string;
  thread_id: string;
  body_plain?: string;
  body_html?: string;
}


const LOCAL_KEY = 'inbox_emails_cache';

const Inbox: React.FC = () => {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const cached = localStorage.getItem(LOCAL_KEY);
    if (cached) {
      try {
        setEmails(JSON.parse(cached));
        setLoading(false);
      } catch {
        localStorage.removeItem(LOCAL_KEY);
      }
    } else {
      fetchEmails();
    }
  }, []);

  // Fetch from API and update localStorage
  const fetchEmails = () => {
    setLoading(true);
    setError(null);
    fetch('http://127.0.0.1:8000/fetch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    })
      .then(res => res.json())
      .then(data => {
        setEmails(data.emails || []);
        localStorage.setItem(LOCAL_KEY, JSON.stringify(data.emails || []));
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to fetch emails.');
        setLoading(false);
      });
  };

  const handleRefresh = () => {
    fetchEmails();
  };

  if (loading) return <div className="loader">Loading emails...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <button onClick={handleRefresh} className="refresh-btn">Refresh</button>
      </div>
      <div className="inbox-list">
        {emails.map(email => (
          <div className="email-card" key={email.id} onClick={() => setSelectedEmail(email)} style={{ cursor: 'pointer' }}>
            <div className="email-from">{email.from}</div>
            <div className="email-subject">{email.subject}</div>
            <div className="email-snippet">{email.snippet}</div>
            <div className="email-date">
              {new Date(Number(email.date)).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Modal for full email body */}
      {selectedEmail && (
        <div className="respond-modal-overlay" onClick={() => setSelectedEmail(null)}>
          <div className="respond-modal" onClick={e => e.stopPropagation()} style={{ minWidth: 350, maxWidth: 600 }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 8 }}>{selectedEmail.subject}</div>
            <div style={{ color: '#38b2ac', fontWeight: 500, marginBottom: 4 }}>From: {selectedEmail.from}</div>
            <div style={{ color: '#888', fontSize: '0.97rem', marginBottom: 8 }}>To: {selectedEmail.to}</div>
            <div style={{ color: '#888', fontSize: '0.97rem', marginBottom: 8 }}>Date: {new Date(Number(selectedEmail.date)).toLocaleString()}</div>
            <div style={{ margin: '1rem 0', color: '#23284a', whiteSpace: 'pre-line', fontSize: '1.01rem' }}>
              {selectedEmail.body_plain || selectedEmail.body_html || selectedEmail.snippet || 'No full email body available.'}
            </div>
            <button className="refresh-btn" style={{ float: 'right' }} onClick={() => setSelectedEmail(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Inbox;
