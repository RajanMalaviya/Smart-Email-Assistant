import React from 'react';
import Tooltip from './Tooltip/Tooltip';

interface SidebarItemProps {
  icon: React.ReactNode;
  label: string;
  tooltip: string;
  selected?: boolean;
  onClick?: () => void;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ icon, label, tooltip, selected = false, onClick }) => {
  return (
    <Tooltip content={tooltip} position="right">
      <div
        className={`sidebar-item${selected ? ' selected' : ''}`}
        onClick={onClick}
        tabIndex={0}
        role="button"
        aria-label={label}
        style={{ outline: 'none' }}
      >
        <span className="sidebar-icon">{icon}</span>
        <span className="sidebar-label">{label}</span>
      </div>
    </Tooltip>
  );
};

export default SidebarItem;
