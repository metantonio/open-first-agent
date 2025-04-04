const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
    setup() {
        const socket = new WebSocket(`ws://${window.location.host}/ws/${uuidv4()}`);
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

        // Initialize ANSI converter
        const ansi_up = new AnsiUp();
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'chat_message':
                    messages.value.push({
                        type: data.sender,
                        content: data.content,
                        timestamp: new Date()
                    });
                    scrollToBottom(messageList);
                    break;
                    
                case 'command_block':
                    messages.value.push({
                        type: 'command',
                        content: `Command ${data.index}: <code>${data.command}</code> (in ${data.working_dir})`,
                        timestamp: new Date()
                    });
                    scrollToBottom(messageList);
                    break;
                    
                case 'terminal_output':
                    terminalLines.value.push({
                        prompt: currentPrompt.value,
                        command: data.command,
                        output: ansi_up.ansi_to_html(data.output)
                    });
                    currentPrompt.value = data.prompt;
                    scrollToBottom(terminalOutput);
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
                    break;
            }
        };

        const sendMessage = () => {
            if(!inputMessage.value.trim()) return;
            
            if(mode.value === 'chat') {
                messages.value.push({
                    type: 'user',
                    content: inputMessage.value,
                    timestamp: new Date()
                });
                
                socket.send(JSON.stringify({
                    type: 'chat_message',
                    content: inputMessage.value
                }));
            } else {
                executeTerminalCommand();
            }
            
            inputMessage.value = '';
            scrollToBottom(mode.value === 'chat' ? messageList : terminalOutput);
        };

        const executeTerminalCommand = () => {
            if(!terminalCommand.value.trim()) return;
            
            socket.send(JSON.stringify({
                type: 'terminal_command',
                command: terminalCommand.value
            }));
            
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

        onMounted(() => {
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
            sendMessage,
            executeTerminalCommand,
            toggleMode,
            clearChat,
            formatTime
        };
    }
}).mount('#app');

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