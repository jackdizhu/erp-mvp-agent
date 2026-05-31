import { useState, useEffect } from 'react';

export default function McpErrorNotification({ error, onDismiss }) {
  const [visible, setVisible] = useState(true);
  
  useEffect(() => {
    if (!error) return;
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, 5000);
    return () => clearTimeout(timer);
  }, [error, onDismiss]);

  if (!error || !visible) return null;

  const isRecoverable = error.recoverable !== false;
  const severity = isRecoverable ? 'warning' : 'error';

  return (
    <div className={`mcp-error-notification ${severity}`}>
      <div className="mcp-error-icon">
        {isRecoverable ? '⚠' : '✕'}
      </div>
      <div className="mcp-error-content">
        <div className="mcp-error-title">
          {error.code || 'MCP_ERROR'}
        </div>
        <div className="mcp-error-message">
          {error.message || 'MCP服务发生错误'}
        </div>
        {error.detail && (
          <div className="mcp-error-detail">
            {error.detail}
          </div>
        )}
      </div>
      <button 
        className="mcp-error-dismiss"
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
      >
        ×
      </button>
    </div>
  );
}