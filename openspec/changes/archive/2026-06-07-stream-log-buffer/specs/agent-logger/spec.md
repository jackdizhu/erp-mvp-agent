## MODIFIED Requirements

### Requirement: Stream chunk logging with buffering
The system SHALL implement buffered stream chunk logging in SessionLogger to reduce log fragmentation. When log_stream_chunk(content) is called, the content SHALL be accumulated in a buffer. The buffer SHALL be flushed (written to file) when either:
1. The buffer size reaches or exceeds STREAM_BUFFER_SIZE (30 characters), OR
2. The time since last write exceeds STREAM_FLUSH_INTERVAL (100ms)

#### Scenario: Buffer reaches threshold
- **WHEN** log_stream_chunk is called and _stream_buffer length + new content >= 30
- **THEN** _flush_stream_buffer() is called immediately, writing all buffered content as one record

#### Scenario: Buffer timeout
- **WHEN** log_stream_chunk is called and _stream_buffer length + new content < 30
- **THEN** a threading.Timer is scheduled to call _delayed_flush after (STREAM_FLUSH_INTERVAL - elapsed) seconds
- **AND** if a previous timer exists, it is cancelled before scheduling a new one

#### Scenario: Immediate flush on existing timer
- **WHEN** log_stream_chunk is called and a _stream_timer is pending
- **THEN** the pending timer is cancelled before adding content to buffer

### Requirement: Thread-safe logging
The system SHALL use threading.Lock to ensure thread-safe access to _stream_buffer and _stream_timer.

#### Scenario: Concurrent chunk logging
- **WHEN** multiple threads call log_stream_chunk simultaneously
- **THEN** each call acquires _stream_lock before modifying buffer, preventing race conditions

### Requirement: Buffer flush on session end
The system SHALL flush any remaining buffered content when the session ends.

#### Scenario: Pending buffer on session end
- **WHEN** a session ends and _stream_buffer has content
- **THEN** _flush_stream_buffer() is called to write remaining content

### Requirement: Backward compatible logging
The system SHALL maintain the same log entry format (type: "stream_chunk", data: {content, length}) for all flushed records.

#### Scenario: Log content integrity
- **WHEN** multiple chunks "订单" + "查询" + "成功" are logged
- **THEN** the flushed record contains "订单查询成功" with length=6 (not three separate records)