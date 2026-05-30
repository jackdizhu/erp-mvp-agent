import { useState } from 'react';

export default function ThinkingIndicator({ stage, message }) {
  return (
    <div className="thinking-indicator">
      <div className="thinking-dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
      <span className="thinking-text">{message || "正在思考..."}</span>
    </div>
  );
}
