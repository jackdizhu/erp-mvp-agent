import { useState, useEffect } from 'react';
import { useSessionManager, createMessage, addAssistantMessage, updateApprovalState, autoTitle, truncateHistory } from './SessionManager';
import ApprovalCard from './ApprovalCard';
import StreamingMessage from './StreamingMessage';
import McpErrorNotification from './McpErrorNotification';
import { useStreamingChat } from './useStreamingChat';
import { chatPost, chatConfirm } from './httpUtils';

const MCP_ERROR_MESSAGES = {
  MCP_SERVICE_UNAVAILABLE: { msg: "ERP服务暂时不可用，请稍后重试", recoverable: true },
  MCP_CONNECTION_TIMEOUT: { msg: "MCP服务连接超时，请稍后重试", recoverable: true },
  MCP_INVALID_RESPONSE: { msg: "MCP服务返回异常，请稍后重试", recoverable: true },
  MCP_TOOL_NOT_FOUND: { msg: "MCP服务不支持此操作", recoverable: false },
  MCP_AUTH_FAILED: { msg: "MCP服务认证失败，请检查配置", recoverable: false },
};

const formatStreamError = (err) => {
  if (err?.isNetworkError || err?.status === 0) {
    return "[网络] 无法连接到服务器，请检查服务是否启动";
  }
  
  const mcpCode = err?.code || err?.error?.code;
  if (mcpCode && MCP_ERROR_MESSAGES[mcpCode]) {
    const mcpInfo = MCP_ERROR_MESSAGES[mcpCode];
    return {
      message: mcpInfo.msg,
      recoverable: mcpInfo.recoverable,
      code: mcpCode
    };
  }
  
  const status = err?.status || 0;
  const message = err?.message || err?.statusText || "未知错误";
  const userMessages = {
    404: "流式接口不存在，请检查服务配置",
    500: "服务器内部错误，请查看后端日志",
    502: "网关错误，后端服务可能未响应",
    503: "服务暂不可用，请稍后重试",
    504: "网关超时，后端处理时间过长"
  };
  const userMsg = userMessages[status];
  if (userMsg) {
    return `[${status}] ${userMsg}`;
  }
  return `[${status}] ${message.slice(0, 100)}`;
};

const QUICK_COMMANDS = [
  { label: "查询订单", template: "查询订单123" },
  { label: "查询库存", template: "查询iPhone-15库存" },
  { label: "批量查询", template: "查询所有订单" },
  { label: "查询供应商", template: "查询供应商SUP-A" },
];

function MessageBubble({ message, messageIndex, activeSession, updateSessions, setLoading, useStream, onConfirm }) {
  const isUser = message.role === "user";

  const handleConfirm = async (actionId, approved) => {
    setLoading(true);
    try {
      const history = truncateHistory(activeSession.messages);
      const data = await chatConfirm(activeSession.id, actionId, approved, history);

      updateSessions(prev => {
        const session = prev.find(s => s.id === activeSession.id);
        if (session) {
          updateApprovalState(session, messageIndex, actionId,
            approved ? (data.error ? "failed" : "success") : "rejected",
            data
          );
          if (data.reply) {
            addAssistantMessage(session, data.reply, data.tool_calls || [], null);
          }
        }
        return [...prev];
      });
    } catch (e) {
      updateSessions(prev => {
        const session = prev.find(s => s.id === activeSession.id);
        if (session) {
          updateApprovalState(session, messageIndex, actionId, "failed");
        }
        return [...prev];
      });
    } finally {
      setLoading(false);
    }
  };

  if (useStream && message.isStreaming !== undefined) {
    return (
      <StreamingMessage
        message={message}
        messageIndex={messageIndex}
        activeSession={activeSession}
        updateSessions={updateSessions}
        setLoading={setLoading}
        onConfirm={handleConfirm}
      />
    );
  }

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="message-content">{message.content}</div>

      {!isUser && message.toolCalls?.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((tc, i) => (
            <div key={i} className="tool-call-item">
              <span className="tool-name">{tc.tool}</span>
              <span className="tool-args">{JSON.stringify(tc.args)}</span>
              {tc.result && (
                <span className="tool-result">→ {JSON.stringify(tc.result).slice(0, 100)}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {!isUser && message.pendingActions?.map((pa) => {
        const state = message.approvalStates?.find(s => s.actionId === pa.action_id);
        return (
          <ApprovalCard
            key={pa.action_id}
            pendingAction={pa}
            approvalState={state}
            onConfirm={() => handleConfirm(pa.action_id, true)}
            onReject={() => handleConfirm(pa.action_id, false)}
          />
        );
      })}
    </div>
  );
}

export default function ChatPage() {
  const {
    sessions, activeSession, activeId,
    handleNewSession, handleSwitchSession, handleDeleteSession,
    updateSessions
  } = useSessionManager();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [useStream, setUseStream] = useState(true);
  const [mcpError, setMcpError] = useState(null);
  const { startStream, stopStream } = useStreamingChat();

  const hasPendingApproval = activeSession?.messages?.some(m =>
    m.approvalStates?.some(s => s.status === "pending")
  );

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    updateSessions(prev => {
      const session = prev.find(s => s.id === activeId);
      if (session) {
        session.title = autoTitle(session, userMsg);
        session.messages.push(createMessage("user", userMsg));
      }
      return [...prev];
    });

    if (useStream) {
      await handleStreamSend(userMsg);
    } else {
      await handleSyncSend(userMsg);
    }
  };

  const handleStreamSend = async (userMsg) => {
    const streamingMsg = {
      role: "assistant",
      content: "",
      isStreaming: true,
      isDone: false,
      replyContent: "",
      toolEvents: [],
      thinkingState: null,
      pendingActions: [],
      approvalStates: [],
      completedTools: [],
      timestamp: new Date().toISOString(),
    };

    updateSessions(prev => {
      const session = prev.find(s => s.id === activeId);
      if (session) {
        session.messages.push(streamingMsg);
      }
      return [...prev];
    });

    let accumulatedReply = "";
    let toolCallOrder = [];
    let thinkDepth = 0;

    const stripThinkContent = (chunk) => {
      let result = "";
      let i = 0;
      while (i < chunk.length) {
        if (chunk.substring(i, i + 7) === "<think>") {
          thinkDepth++;
          i += 7;
        } else if (chunk.substring(i, i + 8) === "</think>") {
          thinkDepth--;
          i += 8;
        } else {
          if (thinkDepth === 0) {
            result += chunk[i];
          }
          i++;
        }
      }
      return result;
    };

    await startStream(userMsg, truncateHistory(activeSession.messages), activeId, {
      onThinking: () => {},
      onToolCall: (data) => {
        if (!toolCallOrder.includes(data.tool)) {
          toolCallOrder.push(data.tool);
        }
        updateSessions(prev => {
          const idx = prev.findIndex(s => s.id === activeId);
          if (idx === -1) return prev;
          const session = { ...prev[idx] };
          const msgs = [...session.messages];
          const msg = { ...msgs[msgs.length - 1] };
          msg.toolEvents = [...msg.toolEvents, { tool: data.tool }];
          msgs[msgs.length - 1] = msg;
          session.messages = msgs;
          prev[idx] = session;
          return [...prev];
        });
      },
      onToolResult: () => {},
      onReplyChunk: (data) => {
        const cleaned = stripThinkContent(data.content);
        accumulatedReply += cleaned;
        updateSessions(prev => {
          const idx = prev.findIndex(s => s.id === activeId);
          if (idx === -1) return prev;
          const session = { ...prev[idx] };
          const msgs = [...session.messages];
          const msg = { ...msgs[msgs.length - 1] };
          msg.replyContent = accumulatedReply;
          msgs[msgs.length - 1] = msg;
          session.messages = msgs;
          prev[idx] = session;
          return [...prev];
        });
      },
      onDone: (data) => {
        const finalContent = accumulatedReply
          .replace(/<think>[\s\S]*?<think>/g, "")
          .trim();
        updateSessions(prev => {
          const idx = prev.findIndex(s => s.id === activeId);
          if (idx === -1) return prev;
          const session = { ...prev[idx] };
          const msgs = [...session.messages];
          const msg = { ...msgs[msgs.length - 1] };
          msg.isStreaming = false;
          msg.isDone = true;
          msg.thinkingState = null;
          msg.completedTools = toolCallOrder;
          msg.toolEvents = toolCallOrder.map(t => ({ tool: t }));
          if (data.error) {
            msg.content = data.error.message || "处理失败，请重试";
            msg.errorMessage = data.error.message || "处理失败，请重试";
            msg.errorRecoverable = data.error.recoverable !== false;
          } else {
            msg.content = finalContent;
            msg.replyContent = "";
          }
          if (data.pending_action) {
            msg.pendingActions = [data.pending_action];
            msg.approvalStates = [{ actionId: data.pending_action.action_id, status: "pending" }];
          }
          msgs[msgs.length - 1] = msg;
          session.messages = msgs;
          prev[idx] = session;
          return [...prev];
        });
        setLoading(false);
      },
      onError: (err) => {
        const errorResult = formatStreamError(err);
        const isMCPError = typeof errorResult === 'object' && errorResult.code;
        const errorMessage = isMCPError ? errorResult.message : errorResult;
        
        if (isMCPError) {
          setMcpError({
            code: errorResult.code,
            message: errorResult.message,
            recoverable: errorResult.recoverable
          });
        }
        
        updateSessions(prev => {
          const idx = prev.findIndex(s => s.id === activeId);
          if (idx === -1) return prev;
          const session = { ...prev[idx] };
          const msgs = [...session.messages];
          const msg = { ...msgs[msgs.length - 1] };
          msg.isStreaming = false;
          msg.isDone = true;
          msg.content = errorMessage;
          msg.thinkingState = null;
          if (isMCPError) {
            msg.mcpError = {
              code: errorResult.code,
              recoverable: errorResult.recoverable
            };
          }
          msgs[msgs.length - 1] = msg;
          session.messages = msgs;
          prev[idx] = session;
          return [...prev];
        });
        setLoading(false);
      }
    });
  };

  const handleSyncSend = async (userMsg) => {
    try {
      const history = truncateHistory(activeSession.messages);
      const data = await chatPost(activeId, userMsg, history);

      updateSessions(prev => {
        const session = prev.find(s => s.id === activeId);
        if (session) {
          addAssistantMessage(session, data.reply, data.tool_calls, data.pending_action);
        }
        return [...prev];
      });
    } catch (e) {
      updateSessions(prev => {
        const session = prev.find(s => s.id === activeId);
        if (session) {
          session.messages.push(createMessage("assistant", "请求失败，请稍后重试"));
        }
        return [...prev];
      });
    } finally {
      setLoading(false);
    }
  };

  const handleQuickCommand = (template) => {
    setInput(template);
  };

  return (
    <div className="chat-page">
      {sidebarOpen && (
        <div className="sidebar">
          <button className="new-session-btn" onClick={handleNewSession}>+ 新建会话</button>
          <div className="session-list">
            {sessions.map(s => (
              <div
                key={s.id}
                className={`session-item ${s.id === activeId ? "active" : ""}`}
                onClick={() => handleSwitchSession(s.id)}
              >
                <span className="session-title">{s.title}</span>
                <button
                  className="delete-btn"
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                >×</button>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="chat-area">
        <McpErrorNotification 
          error={mcpError} 
          onDismiss={() => setMcpError(null)} 
        />
        <div className="chat-header">
          <button className="toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <span>ERP Agent Chat</span>
          <div className="mode-toggle">
            <label>
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
              />
              流式模式
            </label>
          </div>
        </div>
        <div className="message-list">
          {activeSession?.messages?.map((msg, idx) => (
            <MessageBubble
              key={idx}
              message={msg}
              messageIndex={idx}
              activeSession={activeSession}
              updateSessions={updateSessions}
              setLoading={setLoading}
              useStream={useStream}
              onConfirm={async (actionId, approved) => {
                setLoading(true);
                try {
                  const history = truncateHistory(activeSession.messages);
                  const data = await chatConfirm(activeSession.id, actionId, approved, history);

                  updateSessions(prev => {
                    const session = prev.find(s => s.id === activeSession.id);
                    if (session) {
                      updateApprovalState(session, idx, actionId,
                        approved ? (data.error ? "failed" : "success") : "rejected",
                        data
                      );
                      if (data.reply) {
                        addAssistantMessage(session, data.reply, data.tool_calls || [], null);
                      }
                    }
                    return [...prev];
                  });
                } catch (e) {
                  updateSessions(prev => {
                    const session = prev.find(s => s.id === activeSession.id);
                    if (session) {
                      updateApprovalState(session, idx, actionId, "failed");
                    }
                    return [...prev];
                  });
                } finally {
                  setLoading(false);
                }
              }}
            />
          ))}
        </div>
        <div className="quick-commands">
          {QUICK_COMMANDS.map(cmd => (
            <button
              key={cmd.label}
              className="quick-cmd-btn"
              onClick={() => handleQuickCommand(cmd.template)}
            >
              {cmd.label}
            </button>
          ))}
        </div>
        <div className="input-area">
          {hasPendingApproval && (
            <div className="input-hint">请先处理待确认操作</div>
          )}
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            disabled={loading || hasPendingApproval}
            placeholder={hasPendingApproval ? "请先处理待确认操作" : "输入消息..."}
          />
          <button onClick={handleSend} disabled={loading || hasPendingApproval}>
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
