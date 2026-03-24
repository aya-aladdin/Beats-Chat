# Beats - AI Terminal Interface

Beats is a retro-styled, immersive terminal interface for interacting with AI. It combines the nostalgia of command-line computing with modern LLM capabilities, featuring a gamified progression system, multiplayer global chat, and extensive roleplay options.

## 🌟 Features

- **Retro Terminal UI**: Authentic typing effects, command history, and keyboard-driven navigation.
- **AI Chat**: Integrated with Llama 3.1 (via Hack Club Proxy) for intelligent conversations.
- **Personas**: Switch between distinct AI personalities:
  - _Helpful Assistant_
  - _Cocky Genius_
  - _Shy Prodigy_
- **Roleplay Mode**: Define your character, gender, and scenario to start immersive storytelling sessions. (Unlockable!)
- **Global Chat**: Connect with other users in real-time. Supports:
  - `@tagging` users
  - `/me` actions
  - `/whisper` for private messages
- **Progression System**: Earn "Beats" by engaging with the AI. Use them to unlock features like Roleplay Mode.
- **Customization**:
  - Themes: Default, Hacker Green, Amber Retro, Solarized Dark.
  - Adjustable font sizes and response verbosity.
  - Custom User Icons.
- **Local Persistence**: User data and chat history are saved locally in your browser.

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- pip

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/yourusername/beats.git
    cd beats
    ```

2.  Install dependencies:

    ```bash
    pip install flask requests
    ```

3.  Run the application:

    ```bash
    python app.py
    ```

4.  Open your browser and navigate to:
    `http://localhost:5000`

## ⌨️ Usage

### Main Menu Commands

- `[1] Talk to AI`: Standard chat interface.
- `[2] Roleplay Mode`: Specialized storytelling interface (requires unlock).
- `[3] Beats & Upgrades`: Spend your earned beats.
- `[4] Settings`: Configure personas, names, and accessibility.
- `[5] Profile Stats`: View your stats.
- `[6] Global Chat`: Enter the multiplayer room.

### Navigation

- **Type numbers** to select menu options.
- **Arrow Keys** to navigate menus or cycle command history.
- **Click** anywhere to focus the input line.

### Global Chat Commands

- `/me [action]`: Perform an action (e.g., `/me waves`).
- `/whisper [username] [message]`: Send a private message.
- `@[username]`: Tag a user in the chat.

## 🛠️ Tech Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3.
- **Backend**: Python (Flask).
- **AI Provider**: Hack Club Proxy (Meta-Llama-3.1-8B-Instruct).
