const { createApp, ref, onMounted, nextTick } = Vue;

// Configura marked para usar highlight.js
marked.setOptions({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(lang, code).value;
      }
      return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

const app = createApp({
    setup() {
        let socket;
        const messages = ref([]);
        const inputMessage = ref('');
        const mode = ref('chat');
        const sshConnected = ref(false);
        const sshInfo = ref('');
        const terminalLines = ref([]);
        const terminalCommand = ref('');
        const currentPrompt = ref('$ ');
        const messageList = ref(null);
        const terminalOutput = ref(null);
        const isLoading = ref(false);
        const errorMessage = ref(null); // For displaying errors to user
        const ansi_up = new AnsiUp();
        const browserEnabled = ref(true);
        const serverLogs = ref([]);
        const showServerLogs = ref(false);

        // Add this method
        const toggleBrowserAgent = () => {
            browserEnabled.value = !browserEnabled.value;
            try {
                socket.send(JSON.stringify({
                    type: 'toggle_browser',
                    enabled: browserEnabled.value
                }));
            } catch (error) {
                console.error('Error toggling browser agent:', error);
                errorMessage.value = 'Failed to toggle browser agent';
            }
        };
        
        // Initialize WebSocket with error handling
        const initializeWebSocket = () => {
            try {
                socket = new WebSocket(`ws://${window.location.host}/ws/${uuidv4()}`);
                
                socket.onopen = () => {
                    errorMessage.value = null;
                    console.log('WebSocket connection established');
                };
                
                socket.onerror = (error) => {
                    errorMessage.value = 'Connection error. Please refresh the page.';
                    console.error('WebSocket error:', error);
                };
                
                socket.onclose = (event) => {
                    if (!event.wasClean) {
                        errorMessage.value = 'Connection lost. Please refresh the page.';
                        console.error(`WebSocket closed unexpectedly: ${event.code} ${event.reason}`);
                    }
                };
                
                socket.onmessage = async (event) => {
                    console.log('Raw WebSocket message received:', event.data); // Log raw message
                    try {
                        // Handle both string and already-parsed messages
                        if (typeof event.data === 'string') {
                            data = JSON.parse(event.data);
                        } else if (typeof event.data === 'object') {
                            data = event.data;
                        } else {
                            console.error('Unknown message format:', event.data);
                            return;
                        }
                        
                        console.log('Processed message:', data);
                        switch(data.type) {
                            case 'chat_message':
                                let content = data.content;
                                if (data.sender === 'assistant') {
                                    try {
                                        content = marked.parse(data.content);
                                    } catch (markdownError) {
                                        console.error('Error parsing markdown:', markdownError);
                                        content = data.content; // Fallback to raw content
                                    }
                                }
                                
                                messages.value.push({
                                    type: data.sender,
                                    content: content,
                                    timestamp: new Date()
                                });
                                scrollToBottom(messageList);
                                isLoading.value = false;
                                break;
                                
                            case 'command_block':
                                messages.value.push({
                                    type: 'command',
                                    content: `Command ${data.index}: <code>${data.command}</code> (in ${data.working_dir})`,
                                    timestamp: new Date()
                                });
                                scrollToBottom(messageList);
                                isLoading.value = false;
                                break;
                                
                            case 'terminal_output':
                                try {
                                    terminalLines.value.push({
                                        prompt: data.prompt || currentPrompt.value,
                                        command: data.command,
                                        output: ansi_up.ansi_to_html(data.output)
                                    });
                                    currentPrompt.value = data.prompt || currentPrompt.value;
                                    scrollToBottom(terminalOutput);
                                    break;
                                    //currentPrompt.value = data.prompt;
                                    //scrollToBottom(terminalOutput);
                                } catch (ansiError) {
                                    console.error('Error converting ANSI output:', ansiError);
                                    terminalLines.value.push({
                                        prompt: currentPrompt.value,
                                        command: data.command,
                                        output: data.output // Fallback to raw output
                                    });
                                }
                                isLoading.value = false;
                                break;
                                
                            case 'mode_change':
                                mode.value = data.mode;
                                break;
                                
                            case 'ssh_status':
                                sshConnected.value = data.connected;
                                if(data.connected) {
                                    sshInfo.value = `${data.username}@${data.hostname}`;
                                }
                                terminalLines.value.push({
                                    prompt: currentPrompt.value,
                                    command: 'ssh',
                                    output: `<span class="${data.status === 'success' ? 'success' : 'error'}">${data.message}</span>`
                                });
                                currentPrompt.value = terminal_manager.terminal.prompt;
                                scrollToBottom(terminalOutput);
                                isLoading.value = false;
                                break;

                            case 'browser_status':
                                browserEnabled.value = data.enabled;
                                break;

                            case 'server_log':
                                serverLogs.value.push(data.message);
                                console.log('Server log received:', data.message); // Debug
                                // Force Vue to update by creating a new array
                                serverLogs.value = [...serverLogs.value];
                                /* if (serverLogs.value.length > 100) {
                                    serverLogs.value = serverLogs.value.slice(-100);
                                } */
                               // Ensure the log panel scrolls to bottom
                                nextTick(() => {
                                    const logPanel = document.querySelector('.log-content');
                                    if (logPanel) {
                                        logPanel.scrollTop = logPanel.scrollHeight;
                                    }
                                });
                                break;
                                
                            default:
                                console.warn('Unknown message type:', data.type);
                        }
                    } catch (parseError) {
                        console.error('Error parsing WebSocket message:', parseError);
                        errorMessage.value = 'Error processing server response';
                        isLoading.value = false;
                    }
                };
            } catch (wsError) {
                console.error('WebSocket initialization error:', wsError);
                errorMessage.value = 'Failed to connect to server. Please refresh the page.';
            }
        };

        const sendMessage = () => {
            if(!inputMessage.value.trim()) return;
            
            isLoading.value = true;
            if(mode.value === 'chat') {
                messages.value.push({
                    type: 'user',
                    content: inputMessage.value,
                    timestamp: new Date()
                });
                
                try {
                    socket.send(JSON.stringify({
                        type: 'chat_message',
                        content: inputMessage.value
                    }));
                } catch (sendError) {
                    console.error('Error sending chat message:', sendError);
                    errorMessage.value = 'Failed to send message. Please try again.';
                    isLoading.value = false;
                    return;
                }
            } else {
                executeTerminalCommand();
            }
            
            inputMessage.value = '';
            scrollToBottom(mode.value === 'chat' ? messageList : terminalOutput);
        };

        const executeTerminalCommand = () => {
            if(!terminalCommand.value.trim()) return;
            
            try {
                socket.send(JSON.stringify({
                    type: 'terminal_command',
                    command: terminalCommand.value
                }));
            } catch (commandError) {
                console.error('Error sending terminal command:', commandError);
                errorMessage.value = 'Failed to execute command. Please try again.';
                isLoading.value = false;
                return;
            }
            
            terminalCommand.value = '';
        };

        const toggleMode = () => {
            mode.value = mode.value === 'chat' ? 'terminal' : 'chat';
        };

        const clearChat = () => {
            if(mode.value === 'chat') {
                messages.value = [];
            } else {
                terminalLines.value = [];
            }
        };

        const formatTime = (date) => {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        };

        const scrollToBottom = (element) => {
            nextTick(() => {
                if(element.value) {
                    element.value.scrollTop = element.value.scrollHeight;
                }
            });
        };

        const dismissError = () => {
            errorMessage.value = null;
        };

        const toggleServerLogs = () => {
            showServerLogs.value = !showServerLogs.value;
            console.log('Server logs visibility:', showServerLogs.value); // Debug
        };
        
        const clearServerLogs = () => {
            serverLogs.value = [];
        };

        onMounted(() => {
            initializeWebSocket();
            
            // Initialize with welcome message
            messages.value.push({
                type: 'system',
                content: WELCOME_MESSAGE,
                timestamp: new Date()
            });
            
            // Set initial terminal prompt
            currentPrompt.value = terminal_manager.terminal.prompt;
        });

        return {
            messages,
            inputMessage,
            mode,
            sshConnected,
            sshInfo,
            terminalLines,
            terminalCommand,
            currentPrompt,
            messageList,
            terminalOutput,
            errorMessage,
            sendMessage,
            executeTerminalCommand,
            toggleMode,
            clearChat,
            formatTime,
            isLoading,
            dismissError,
            browserEnabled,
            toggleBrowserAgent,
            serverLogs,
            showServerLogs,
            toggleServerLogs,
            clearServerLogs
        };
    }
    
}).mount('#app');

app.config.compilerOptions.delimiters = ['{{{', '}}}'];

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}



const WELCOME_MESSAGE = `👋 Welcome to the AI Assistant!

I can help you with various tasks:

1. 🌐 Web Search and News
2. 🏗️ Terraform Infrastructure
3. 💻 Development Environment Setup
4. ☁️ AWS CLI Configuration
5. 📂 File System Operations
6. 🖥️ Terminal Interface

Type your request or toggle terminal mode to use terminal commands.
Use ! prefix to execute terminal commands in chat mode.`;