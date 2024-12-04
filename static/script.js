document.addEventListener('DOMContentLoaded', () => {
    const messagesContainer = document.querySelector('.messages');
    const messageInput = document.querySelector('.message-input input');
    const instancesContainer = document.querySelector('.online-users');
    const clearButton = document.querySelector('.nav-icons .icon.clear');

    // Configure marked options
    marked.setOptions({
        gfm: true,
        breaks: true,
        highlight: function(code, lang) {
            if (window.hljs) {
                try {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(lang, code).value;
                    } else {
                        return hljs.highlightAuto(code).value;
                    }
                } catch (e) {}
            }
            return code;
        }
    });

    // Function to format timestamp
    function formatTimestamp(date) {
        const today = new Date();
        const messageDate = new Date(date);
        
        if (today.toDateString() === messageDate.toDateString()) {
            return messageDate.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit'
            });
        }
        return messageDate.toLocaleDateString('en-US', { 
            month: 'numeric',
            day: 'numeric',
            year: 'numeric'
        });
    }

    // Function to safely convert markdown to HTML
    function markdownToHtml(text) {
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown parsing error:', e);
            showErrorToast('Error parsing Markdown.');
            return text;
        }
    }

    // Function to create a message element
    function createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        const timestamp = formatTimestamp(new Date());

        if (message.role === 'user') {
            const content = markdownToHtml(message.content);
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-avatar" style="background-color: #5865f2;">
                        <span style="color: white; font-weight: bold;">U</span>
                    </div>
                    <div class="message-main">
                        <div class="message-header">
                            <span class="message-author">User</span>
                            <span class="message-timestamp">Today at ${timestamp}</span>
                        </div>
                        <div class="message-text markdown">${content}</div>
                    </div>
                </div>
            `;

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';

            const editButton = document.createElement('button');
            editButton.className = 'edit-button';
            editButton.textContent = 'Edit';
            editButton.addEventListener('click', () => editMessage(message, messageDiv));

            const deleteButton = document.createElement('button');
            deleteButton.className = 'delete-button';
            deleteButton.textContent = 'Delete';
            deleteButton.addEventListener('click', () => deleteMessage(message, messageDiv));

            actionsDiv.appendChild(editButton);
            actionsDiv.appendChild(deleteButton);

            messageDiv.querySelector('.message-main').appendChild(actionsDiv);

            return messageDiv;
        }

        // Handle error messages specially
        if (message.error) {
            messageDiv.innerHTML = `
                <div class="message-content error">
                    <div class="message-avatar" style="background-color: #ed4245;">
                        <span style="color: white; font-weight: bold;">⚠️</span>
                    </div>
                    <div class="message-main">
                        <div class="message-header">
                            <span class="message-author">Error</span>
                            <span class="message-timestamp">Today at ${timestamp}</span>
                        </div>
                        <div class="message-text error">${message.error}</div>
                    </div>
                </div>
            `;
            return messageDiv;
        }

        // Handle AI assistant and other AI instances
        const icon = message.icon || '🤖';
        const role = message.role.charAt(0).toUpperCase() + message.role.slice(1).replace(/-/g, ' ');
        const bgColor = message.role === 'assistant' ? '#5865f2' : '#23a559';

        const content = markdownToHtml(message.content);

        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-avatar" style="background-color: ${bgColor};">
                    <span style="color: white; font-weight: bold;">${icon}</span>
                </div>
                <div class="message-main">
                    <div class="message-header">
                        <span class="message-author">${role}</span>
                        <span class="message-timestamp">Today at ${timestamp}</span>
                    </div>
                    <div class="message-text markdown">${content}</div>
                </div>
            </div>
        `;
        return messageDiv;
    }

    // Function to update instances list
    function updateInstances(instances) {
        instancesContainer.innerHTML = '';
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'activity-header';
        headerDiv.textContent = 'ACTIVITY — 1';
        instancesContainer.appendChild(headerDiv);

        const instancesCountDiv = document.createElement('div');
        instancesCountDiv.className = 'active-instances';
        const totalInstances = (instances.instances || []).length + (instances.mother_node ? 1 : 0);
        instancesCountDiv.textContent = `ACTIVE NODES — ${totalInstances}`;
        instancesContainer.appendChild(instancesCountDiv);
        
        if (instances.mother_node) {
            const motherDiv = document.createElement('div');
            motherDiv.className = 'user';
            motherDiv.innerHTML = `
                <div class="user-avatar" style="background-color: #71368a;">
                    <span>${instances.mother_node.icon || '👨‍💼'}</span>
                    <div class="status-indicator" style="background-color: #71368a;"></div>
                </div>
                <div class="user-info">
                    <div class="user-name">
                        Scrum Master
                        <span>${instances.mother_node.id}</span>
                    </div>
                    <div class="user-status">Active Node</div>
                </div>
            `;
            instancesContainer.appendChild(motherDiv);
        }
        
        if (instances.instances) {
            instances.instances.forEach(instance => {
                const instanceDiv = document.createElement('div');
                instanceDiv.className = 'user';
                
                instanceDiv.innerHTML = `
                    <div class="user-avatar" style="background-color: #23a559;">
                        <span>${instance.icon || '🤖'}</span>
                        <div class="status-indicator" style="background-color: #23a559;"></div>
                    </div>
                    <div class="user-info">
                        <div class="user-name">
                            ${instance.role.charAt(0).toUpperCase() + instance.role.slice(1).replace(/-/g, ' ')}
                            <span>${instance.id}</span>
                        </div>
                        <div class="user-status">Active Node</div>
                    </div>
                `;
                instancesContainer.appendChild(instanceDiv);
            });
        }
    }

    // Function to fetch current instances
    async function fetchInstances() {
        try {
            const response = await fetch('/api/instances');
            if (!response.ok) {
                const data = await response.json();
                if (response.status === 503) {
                    showErrorToast('System is initializing. Please wait...');
                    return;
                }
                throw new Error(data.error || 'Failed to fetch instances');
            }
            const data = await response.json();
            updateInstances(data);
        } catch (error) {
            console.error('Error fetching instances:', error);
            showErrorToast(error.message);
        }
    }

    // Function to scroll messages into view
    function scrollMessagesIntoView() {
        const lastMessage = messagesContainer.firstElementChild;
        if (lastMessage) {
            lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }

    // Load messages from local storage
    const savedMessages = JSON.parse(localStorage.getItem('chatMessages')) || [];
    savedMessages.forEach(messageData => {
        const messageElement = createMessageElement(messageData);
        messagesContainer.insertBefore(messageElement, messagesContainer.firstChild);
    });

    // Function to add a message with animation
    function addMessageWithAnimation(messageElement, messageData) {
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(20px)';
        messageElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        
        messagesContainer.insertBefore(messageElement, messagesContainer.firstChild);

        savedMessages.push(messageData);
        localStorage.setItem('chatMessages', JSON.stringify(savedMessages));
        
        messageElement.offsetHeight;
        
        messageElement.style.opacity = '1';
        messageElement.style.transform = 'translateY(0)';
        
        scrollMessagesIntoView();
    }

    // Function to add responses sequentially
    async function addResponsesSequentially(responses) {
        for (const response of responses) {
            const messageElement = createMessageElement(response);
            addMessageWithAnimation(messageElement, response);
            await new Promise(resolve => setTimeout(resolve, 750));
        }
    }

    // Show loading indicator during API calls
    async function sendMessage(content) {
        if (!content.trim()) return;

        showLoadingSpinner();
        
        const userMessageElement = createMessageElement({
            role: 'user',
            content: content
        });
        addMessageWithAnimation(userMessageElement, { role: 'user', content: content });

        try {
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: content
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                // Handle specific error status codes
                if (response.status === 503) {
                    showErrorToast('System is still initializing. Please wait a moment...');
                } else if (response.status === 504) {
                    showErrorToast('Request timed out. Please try again.');
                } else {
                    showErrorToast(data.error || 'Failed to process message');
                }
                
                // Add error message to chat
                const errorElement = createMessageElement({
                    error: data.error || 'Failed to process message'
                });
                addMessageWithAnimation(errorElement, { error: data.error });
                return;
            }

            if (data.responses) {
                await addResponsesSequentially(data.responses);
            }

            if (data.instances) {
                updateInstances(data.instances);
            }

        } catch (error) {
            console.error('Error sending message:', error);
            showErrorToast('Network error. Please check your connection.');
            
            const errorElement = createMessageElement({
                error: 'Network error. Please check your connection.'
            });
            addMessageWithAnimation(errorElement, { error: 'Network error' });
        } finally {
            hideLoadingSpinner();
        }
    }

    // Function to clear chat and reset nodes
    async function clearAll() {
        try {
            const response = await fetch('/api/clear', {
                method: 'POST'
            });
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to clear chat');
            }
            
            messagesContainer.innerHTML = '';
            localStorage.setItem('chatMessages', '[]');
            await fetchInstances();
            
        } catch (error) {
            console.error('Error clearing chat:', error);
            showErrorToast(error.message);
        }
    }

    // Handle message input
    messageInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const content = messageInput.value;
            messageInput.value = '';
            await sendMessage(content);
        }
    });

    // Implement typing indicator
    let typingTimeout;
    messageInput.addEventListener('input', () => {
        fetch('/api/typing', { method: 'POST' });
        showTypingIndicator();
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(hideTypingIndicator, 2000);
    });

    // Handle clear button click
    clearButton.addEventListener('click', clearAll);

    // Initial fetch of instances
    fetchInstances();

    // Periodically update instances with a longer interval (every 10 seconds instead of 5)
    setInterval(fetchInstances, 10000);
});

// Functions to show/hide loading spinner
function showLoadingSpinner() {
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) spinner.style.display = 'block';
}

function hideLoadingSpinner() {
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) spinner.style.display = 'none';
    hideTypingIndicator();
}

// Functions to show/hide typing indicator
function showTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) typingIndicator.style.display = 'block';
}

function hideTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) typingIndicator.style.display = 'none';
}

function showErrorToast(message) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'toast error';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

function editMessage(messageData, messageElement) {
    const newContent = prompt('Edit your message:', messageData.content);
    if (newContent !== null && newContent !== messageData.content) {
        messageData.content = newContent;
        messageElement.querySelector('.message-text').innerHTML = markdownToHtml(newContent);

        localStorage.setItem('chatMessages', JSON.stringify(savedMessages));

        fetch('/api/edit_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: messageData.id, new_content: newContent })
        }).catch(error => {
            console.error('Error updating message:', error);
            showErrorToast('Failed to update message on server');
        });
    }
}

function deleteMessage(messageData, messageElement) {
    if (confirm('Are you sure you want to delete this message?')) {
        messageElement.remove();

        const index = savedMessages.indexOf(messageData);
        if (index > -1) {
            savedMessages.splice(index, 1);
            localStorage.setItem('chatMessages', JSON.stringify(savedMessages));
        }

        fetch('/api/delete_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: messageData.id })
        }).catch(error => {
            console.error('Error deleting message:', error);
            showErrorToast('Failed to delete message on server');
        });
    }
}
