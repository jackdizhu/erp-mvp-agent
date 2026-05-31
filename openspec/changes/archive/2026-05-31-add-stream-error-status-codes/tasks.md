## 1. Backend Error Logging Enhancement

- [ ] 1.1 Add logging import and error logging to `app/main.py` stream_endpoint exception handler
- [ ] 1.2 Enhance `app/clients/mcp_client.py` to log detailed HTTP status code, URL, and response content on request failures

## 2. Frontend Error Object Enhancement

- [ ] 2.1 Modify `frontend/src/httpUtils.js` chatStreamReader to construct detailed error object with status, statusText, message on HTTP failure
- [ ] 2.2 Update `frontend/src/useStreamingChat.js` to pass through the enhanced error object to onError callback

## 3. Frontend Error Display

- [ ] 3.1 Update `frontend/src/ChatPage.jsx` onError callback to display formatted error message with status code
- [ ] 3.2 Add status-code-specific user-friendly messages (e.g., 404 → service not started, 500 → server error, 0 → network failure)
