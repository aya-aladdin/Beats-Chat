DROP TABLE IF EXISTS chat_history;
DROP TABLE IF EXISTS global_messages;

CREATE TABLE chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL
);

CREATE TABLE global_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL,
  content TEXT NOT NULL,
  msg_type TEXT,
  recipient TEXT,
  "time" TEXT,
  "type" TEXT,
  "user" TEXT
);
