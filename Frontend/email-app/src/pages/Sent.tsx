import React, { useEffect, useState } from 'react';
import '../styles/Sent.css';

interface GmailResponse {
  id: string;
  threadId: string;
  labelIds: string[];
}
interface RespondedEmail {
  email_id: string;
  thread_id: string;
  to: string;
  from: string;
  subject: string;
  body: string;
  status: string;
  edited_by_human: boolean;
  created_at: string;
  sent_at: string;
  gmail_response: GmailResponse;
}

const Sent: React.FC = () => {
  const [emails, setEmails] = useState<RespondedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/responded-emails')
      .then(res => res.json())
      .then(data => {
        setEmails(data.responded_emails || []);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to fetch sent emails.');
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="loader">Loading sent emails...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="sent-list">
      {emails
        .slice()
        .sort((a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime())
        .map((email, idx) => (
        <div className="sent-card" key={email.gmail_response.id || idx}>
          <div className="sent-header">
            <span className="sent-to"><b>To:</b> {email.to}</span>
            <span className="sent-status">{email.status.toUpperCase()}</span>
          </div>
          <div className="sent-subject">{email.subject}</div>
          <div className="sent-body">{email.body}</div>
          <div className="sent-date">
            Sent: {new Date(email.sent_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
};

export default Sent;
