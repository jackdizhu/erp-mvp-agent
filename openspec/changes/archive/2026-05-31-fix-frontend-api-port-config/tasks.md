## 1. Environment Configuration

- [x] 1.1 Create `frontend/.default.env` with `VITE_API_PORT=9000`
- [x] 1.2 Create `frontend/.development.env` with `VITE_API_PORT=9000`

## 2. Code Change

- [x] 2.1 Modify `frontend/src/httpUtils.js` to use `import.meta.env.VITE_API_PORT` instead of hardcoded port
