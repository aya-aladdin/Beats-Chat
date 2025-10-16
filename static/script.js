document.addEventListener('DOMContentLoaded', () => {
    const output = document.getElementById('output');
    const inputLine = document.getElementById('input-line');
    const terminal = document.getElementById('terminal');
    const hiddenInput = document.getElementById('hidden-input');

    let commandHistory = [];
    let historyIndex = -1;
    let currentInput = "";
    let isExecuting = false;
    let abortController = new AbortController();

    const PROMPT = `<span class="text-cyan-400">&gt;</span>`;

    // --- Core Functions ---

    const focusInput = () => {
        hiddenInput.focus();
    };

    terminal.addEventListener('click', () => {
        // Don't refocus if the user is selecting text
        if (window.getSelection().toString().length === 0) {
            focusInput();
        }
    });

    const typeEffect = async (element, text, delay = 15) => {
        return new Promise(resolve => {
            let i = 0;
            function typing() {
                if (i < text.length) {
                    element.innerHTML += text.charAt(i);
                    i++;
                    setTimeout(typing, Math.random() * delay + 10);
                    terminal.scrollTop = terminal.scrollHeight;
                } else {
                    resolve();
                }
            }
            typing();
        });
    };

    const processCommand = async (command) => {
        addToOutput(`${PROMPT} ${command}`);
        commandHistory.unshift(command);
        historyIndex = -1;
        isExecuting = true;

        const [cmd, ...args] = command.trim().split(' ');

        switch (cmd.toLowerCase()) {
            case 'clear':
                output.innerHTML = '';
                break;
            case 'help':
                const helpText = `Available commands:\n` +
                    `  help          - Shows this help message.\n` +
                    `  clear         - Clears the terminal screen.\n` +
                    `  about         - Displays information about this terminal.\n` +
                    `  credits       - Shows project credits.\n` +
                    `  theme         - Toggles the color theme.\n` +
                    `  ask "[prompt]"- Ask the AI something.\n` +
                    `  (or just type your question directly)`;
                await typeEffect(createResponseElement(), helpText);
                break;
            case 'about':
                await typeEffect(createResponseElement(), "Aya's AI Terminal v1.0\nAn interactive, terminal-style AI assistant.");
                break;
            case 'credits':
                await typeEffect(createResponseElement(), "Built by Aya. Powered by Hack Club's AI API.");
                break;
            case 'theme':
                document.body.classList.toggle('theme-cyan');
                document.body.classList.toggle('theme-green');
                await typeEffect(createResponseElement(), `Theme toggled.`);
                break;
            // Easter Eggs
            case 'hackclub':
                const logo = `
      .cccc;;cccc;
   ,ccclllllllllcccc.
 ,cllllllllllllllllll.
;cllllllllllllllllllll;
;llllllllllllllllllllll;
;llllllllllllllllllllll;
.clllllllllllllllllllc.
  .clllllllllllllllc.
     .cllllllllll.
`;
                await typeEffect(createResponseElement(), logo, 1);
                break;
            case 'sudo':
                if (args.join(' ') === 'ask "meaning of life"') {
                    await typeEffect(createResponseElement(), "42");
                    break;
                }
            default:
                await fetchAIResponse(command);
                break;
        }

        isExecuting = false;
        currentInput = "";
        inputLine.textContent = "";
    };

    const fetchAIResponse = async (prompt) => {
        const responseElement = createResponseElement();
        abortController = new AbortController(); // New controller for each request

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt }),
                signal: abortController.signal
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: true });
                    responseElement.innerHTML += chunk.replace(/\n/g, '<br>');
                    terminal.scrollTop = terminal.scrollHeight;
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                responseElement.innerHTML += '\n<span class="text-red-500">[Execution stopped]</span>';
            } else {
                responseElement.textContent = `Error: ${error.message}`;
            }
        }
    };

    // --- Utility Functions ---

    const addToOutput = (html) => {
        output.innerHTML += `<div>${html}</div>`;
        terminal.scrollTop = terminal.scrollHeight;
    };

    const createResponseElement = () => {
        const div = document.createElement('div');
        div.classList.add('response');
        output.appendChild(div);
        return div;
    };

    // --- Event Handlers ---

    document.addEventListener('keydown', (e) => {
        if (isExecuting) {
            if (e.ctrlKey && e.key === 'c') {
                abortController.abort();
            }
            return;
        }

        if (e.key === 'Enter') {
            if (currentInput.trim()) {
                processCommand(currentInput);
            }
        } else if (e.key === 'Backspace') {
            currentInput = currentInput.slice(0, -1);
            inputLine.textContent = currentInput;
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                currentInput = commandHistory[historyIndex];
                inputLine.textContent = currentInput;
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                currentInput = commandHistory[historyIndex];
                inputLine.textContent = currentInput;
            } else {
                historyIndex = -1;
                currentInput = "";
                inputLine.textContent = "";
            }
        } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
            currentInput += e.key;
            inputLine.textContent = currentInput;
        }
    });

    // --- Initial Boot Sequence ---
    const boot = async () => {
        isExecuting = true;
        await typeEffect(createResponseElement(), "Booting Aya's AI Terminal...", 50);
        await typeEffect(createResponseElement(), "Connecting to network...", 50);
        await typeEffect(createResponseElement(), "Connection established ✅", 50);
        await typeEffect(createResponseElement(), "Aya is online. Awaiting input, operator.", 20);
        isExecuting = false;
        focusInput();
    };

    // Set initial theme and start
    document.body.classList.add('theme-green');
    boot();
});
