import React, { useEffect, useState } from 'react';
interface RespondResult {
  status: string;
  email_id: string;
  to: string;
  from: string;
  subject: string;
  draft: string;
  gmail_response: {
    id: string;
    threadId: string;
    labelIds: string[];
  };
}
import '../styles/Classify.css';

interface ClassifiedEmail {
  id: string;
  from: string;
  to: string[];
  subject: string;
  snippet: string;
  date: string | null;
  thread_id: string;
  category: string;
  confidence?: number;
  reasoning?: string | null;
  summary?: string | null;
}

const LOCAL_KEY = 'classified_emails_cache';

const Classify: React.FC = () => {
  const [respondModal, setRespondModal] = useState<null | RespondResult>(null);
  const [emails, setEmails] = useState<ClassifiedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alert, setAlert] = useState<string | null>(null);


  // On mount, fetch classified emails from MongoDB (GET endpoint)
  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch('http://127.0.0.1:8000/classified-emails')
      .then(res => res.json())
      .then(data => {
        setEmails(data.classified_emails || []);
        localStorage.setItem(LOCAL_KEY, JSON.stringify(data.classified_emails || []));
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to fetch classified emails from database.');
        setLoading(false);
      });
  }, []);

  // Only call classify API on button click
  const handleClassify = () => {
    setLoading(true);
    setError(null);
    setAlert(null);
    fetch('http://127.0.0.1:8000/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
      .then(res => res.json())
      .then(data => {
        // Merge new classified emails with existing, avoiding duplicates by id
        const newEmails: ClassifiedEmail[] = data.classified_emails || [];
        const existingById = new Map(emails.map(e => [e.id, e]));
        newEmails.forEach((e: ClassifiedEmail) => existingById.set(e.id, e));
        const merged = Array.from(existingById.values());
        setEmails(merged);
        localStorage.setItem(LOCAL_KEY, JSON.stringify(merged));
        setLoading(false);
        if (newEmails.length === 0) {
          setAlert('No Unclassified Email found');
        } else if (newEmails.length === 1) {
          setAlert('1 Email classified successfully');
        } else {
          setAlert(`${newEmails.length} Emails classified successfully`);
        }
        setTimeout(() => setAlert(null), 3500);
      })
      .catch(() => {
        setError('Failed to classify emails.');
        setLoading(false);
      });
  };

  const [expanded, setExpanded] = useState<string | null>(null);

  if (loading) return <div className="loader">Loading classified emails...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div>
      {alert && (
        <div className="classify-alert">{alert}</div>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem', gap: '1rem' }}>
        <button onClick={handleClassify} className="refresh-btn">Classify</button>
      </div>
      <div className="classify-list">
        {emails
          .slice()
          .sort((a, b) => {
            // If both dates exist, sort by date descending
            if (a.date && b.date) {
              return Number(b.date) - Number(a.date);
            }
            // If only one has a date, that one comes first
            if (a.date) return -1;
            if (b.date) return 1;
            // Otherwise, keep original order
            return 0;
          })
          .map((email, idx) => {
            const isOpen = expanded === email.id;
            return (
              <div
                className={`classify-card${isOpen ? ' expanded' : ''}`}
                key={email.id || idx}
                onClick={() => setExpanded(isOpen ? null : email.id)}
                style={{ cursor: 'pointer', position: 'relative' }}
              >
                <div className="classify-header">
                  <span className="classify-from">{email.from}</span>
                  <span className="classify-category">{email.category}</span>
                  <span className="classify-confidence">
                    {email.confidence ? `${(email.confidence * 100).toFixed(0)}%` : 'N/A'}
                  </span>
                </div>
                <div className="classify-subject">{email.subject}</div>
                <div className="classify-snippet">{email.snippet}</div>
                {isOpen && email.summary && (
                  <div className="classify-summary"><b>Summary:</b> {email.summary}</div>
                )}
                {isOpen && email.reasoning && (
                  <div className="classify-reasoning"><b>Reasoning:</b> {email.reasoning}</div>
                )}
                <div className="classify-card-footer">
                  <button
                    className="respond-btn"
                    onClick={async e => {
                      e.stopPropagation();
                      const draft = window.prompt('Enter your response:', '');
                      if (!draft) return;
                      try {
                        const res = await fetch('http://127.0.0.1:8000/respond', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ email_id: email.id, draft }),
                        });
                        const data: RespondResult = await res.json();
                        if (data.status === 'sent') {
                          setRespondModal(data);
                        } else {
                          window.alert('Failed to send response.');
                        }
                      } catch {
                        window.alert('Failed to send response.');
                      }
                    }}
                    tabIndex={0}
                    title="Respond"
                  >Respond</button>
                </div>
      {respondModal && (
        <div className="respond-modal-overlay" onClick={() => setRespondModal(null)}>
          <div className="respond-modal" onClick={e => e.stopPropagation()}>
            <h2>Response Sent!</h2>
            <div><b>To:</b> {respondModal.to}</div>
            <div><b>Subject:</b> {respondModal.subject}</div>
            <div><b>Draft:</b>
              <pre style={{ background: '#f4f6fa', padding: '0.7em', borderRadius: '6px', marginTop: '0.3em' }}>{respondModal.draft}</pre>
            </div>
            <div><b>Gmail Message ID:</b> {respondModal.gmail_response.id}</div>
            <button style={{ marginTop: '1.2em' }} onClick={() => setRespondModal(null)}>Close</button>
          </div>
        </div>
      )}
              </div>
            );
          })}
      </div>
    </div>
  );
};

export default Classify;
