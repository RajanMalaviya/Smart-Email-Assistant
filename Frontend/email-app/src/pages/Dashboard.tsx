import React, { useState } from 'react';
import Sidebar from '../components/Sidebar/Sidebar';
import '../styles/Dashboard.css';
import Inbox from './Inbox';
import Classify from './Classify';
import Sent from './Sent';

const Dashboard: React.FC = () => {
  const [selectedSection, setSelectedSection] = useState('Inbox');
  // const [searchQuery, setSearchQuery] = useState('');

  // Placeholder for main content based on selected section
  const renderContent = () => {
    switch (selectedSection) {
      case 'Inbox':
        return <Inbox />;
      case 'Classify':
        return <Classify />;
      case 'Sent':
        return <Sent />;
      default:
        return null;
    }
  };

  // Dynamic header/subheader
  let header = '';
  let subheader = '';
  switch (selectedSection) {
    case 'Inbox':
      header = 'Inbox';
      subheader = 'All Emails from your Gmail will be listed here';
      break;
    case 'Classify':
      header = 'Classified Emails';
      subheader = 'Classified Emails with AI Assistance';
      break;
    case 'Sent':
      header = 'Sent Emails';
      subheader = 'All Sent Emails by AI Assistant will be listed here';
      break;
    default:
      header = '';
      subheader = '';
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-sidebar">
        <Sidebar onSelect={setSelectedSection} selected={selectedSection} />
      </div>
      <div className="dashboard-main">
        <div className="dashboard-header-block">
          <h1 className="dashboard-header">{header}</h1>
          <div className="dashboard-subheader">{subheader}</div>
        </div>
        <div className="dashboard-content">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
