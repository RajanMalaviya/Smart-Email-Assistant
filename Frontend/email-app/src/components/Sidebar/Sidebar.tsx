import React from 'react';
import { MdInbox, MdSend, MdLabel } from 'react-icons/md';
import './Sidebar.css';

const sidebarItems = [
  { label: 'Inbox', icon: <MdInbox />, tooltip: 'View your inbox' },
  { label: 'Classify', icon: <MdLabel />, tooltip: 'Classify emails' },
  { label: 'Sent', icon: <MdSend />, tooltip: 'View sent emails' },
];

const Sidebar: React.FC<{ onSelect: (section: string) => void; selected: string }> = ({ onSelect, selected }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">Smart Email</div>
      <nav>
        {sidebarItems.map((item) => (
          <div
            key={item.label}
            className={`sidebar-item${selected === item.label ? ' selected' : ''}`}
            title={item.tooltip}
            onClick={() => onSelect(item.label)}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span className="sidebar-label">{item.label}</span>
          </div>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
