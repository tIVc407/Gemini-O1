document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const messagesContainer = document.querySelector('.messages');
    const messageInput = document.querySelector('.message-input textarea');
    const sendButton = document.querySelector('.send-button');
    const instancesContainer = document.querySelector('.online-users');
    const clearButton = document.querySelector('.icon-btn.clear');
    const menuToggle = document.querySelector('.menu-toggle');
    const appContainer = document.querySelector('.app-container');
    const themeToggle = document.querySelector('.theme-toggle');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const workflowDiagram = document.querySelector('.workflow-diagram');
    const chatArea = document.querySelector('.messages');
    const quickPrompts = document.querySelectorAll('.prompt-chip');
    const nodeFilters = document.querySelectorAll('.node-filter');
    const refreshNodesBtn = document.querySelector('.refresh-nodes');
    const formatButtons = document.querySelectorAll('.formatting-toolbar button');
    const settingsModal = document.getElementById('settings-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const exportBtn = document.querySelector('[title="Export Conversation"]');
    const shareBtn = document.querySelector('[title="Share Conversation"]');
    const nodesCountElement = document.getElementById('nodes-count');
    const messagesCountElement = document.getElementById('messages-count');
    const apiCallsElement = document.getElementById('api-calls');
    const lastUpdatedElement = document.getElementById('last-updated');
    const uploadFileBtn = document.getElementById('upload-file-btn');
    const fileUploadInput = document.getElementById('file-upload');
    
    // File upload variables
    let currentUploadedFile = null;

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
        const type = message.type || 'normal';
        
        // Add status indicator based on message type
        let statusIndicator = '';
        if (type === 'planning') {
            statusIndicator = '<span class="status-badge planning">Planning</span>';
        } else if (type === 'specialist') {
            statusIndicator = '<span class="status-badge specialist">Specialist</span>';
        } else if (type === 'synthesis') {
            statusIndicator = '<span class="status-badge synthesis">Synthesis</span>';
        }

        const content = markdownToHtml(message.content);

        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-avatar" style="background-color: ${bgColor};">
                    <span style="color: white; font-weight: bold;">${icon}</span>
                </div>
                <div class="message-main">
                    <div class="message-header">
                        <span class="message-author">${role}</span>
                        ${statusIndicator}
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
            
            // Update session stats if available
            if (data.stats) {
                nodesCountElement.textContent = data.stats.total_instances;
                messagesCountElement.textContent = data.stats.total_messages;
                apiCallsElement.textContent = data.stats.api_usage ? data.stats.api_usage.total_calls : '0';
                
                // Update last updated time
                updateLastUpdated();
            }
            
            // If we're in workflow mode, update the network visualization
            const workflowActive = document.querySelector('.workflow-diagram').style.display !== 'none';
            if (workflowActive) {
                updateWorkflowVisualization(data);
            }
        } catch (error) {
            console.error('Error fetching instances:', error);
            showErrorToast(error.message);
        }
    }
    
    // Function to fetch detailed network stats
    async function fetchNetworkStats() {
        try {
            const response = await fetch('/api/network/stats');
            if (!response.ok) {
                throw new Error('Failed to fetch network statistics');
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching network stats:', error);
            return null;
        }
    }
    
    // Function to update the workflow visualization
    function updateWorkflowVisualization(instancesData) {
        const workflowDiagram = document.querySelector('.workflow-diagram');
        
        // Clear previous visualization
        if (workflowDiagram.querySelector('svg')) {
            workflowDiagram.querySelector('svg').remove();
        }
        
        // Remove placeholder if it exists
        const placeholder = workflowDiagram.querySelector('.diagram-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        // Width and height of the diagram
        const width = workflowDiagram.clientWidth;
        const height = workflowDiagram.clientHeight || 500;
        
        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('class', 'network-graph');
        workflowDiagram.appendChild(svg);
        
        // Prepare nodes and links
        const nodes = [];
        const links = [];
        
        // Add mother node
        if (instancesData.mother_node) {
            nodes.push({
                id: instancesData.mother_node.id,
                name: 'Scrum Master',
                role: instancesData.mother_node.role,
                icon: instancesData.mother_node.icon || '👨‍💼',
                color: '#8942C1',
                radius: 30
            });
        }
        
        // Add instances
        if (instancesData.instances) {
            instancesData.instances.forEach(instance => {
                nodes.push({
                    id: instance.id,
                    name: instance.role,
                    role: instance.role,
                    icon: instance.icon || '🤖',
                    color: '#5865f2',
                    radius: 25
                });
            });
        }
        
        // Create links based on connected_to property
        if (instancesData.mother_node && instancesData.mother_node.connected_to) {
            instancesData.mother_node.connected_to.forEach(targetId => {
                links.push({
                    source: instancesData.mother_node.id,
                    target: targetId
                });
            });
        }
        
        if (instancesData.instances) {
            instancesData.instances.forEach(instance => {
                if (instance.connected_to) {
                    instance.connected_to.forEach(targetId => {
                        // Avoid duplicate links
                        const isDuplicate = links.some(link => 
                            (link.source === instance.id && link.target === targetId) || 
                            (link.source === targetId && link.target === instance.id)
                        );
                        
                        if (!isDuplicate) {
                            links.push({
                                source: instance.id,
                                target: targetId
                            });
                        }
                    });
                }
            });
        }
        
        // Only proceed if we have nodes
        if (nodes.length === 0) return;
        
        // Create D3 force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-500))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => d.radius + 10));
        
        // Create the links
        const link = d3.select(svg)
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', '#555')
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.6);
        
        // Create the nodes
        const node = d3.select(svg)
            .selectAll('.node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        // Add circles for nodes
        node.append('circle')
            .attr('r', d => d.radius)
            .attr('fill', d => d.color)
            .attr('stroke', '#222')
            .attr('stroke-width', 2);
        
        // Add icons to nodes
        node.append('text')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'central')
            .attr('fill', 'white')
            .attr('font-size', '20px')
            .text(d => d.icon);
        
        // Add labels below nodes
        node.append('text')
            .attr('text-anchor', 'middle')
            .attr('y', d => d.radius + 15)
            .attr('fill', 'white')
            .attr('font-size', '12px')
            .text(d => d.name);
        
        // Animation functions for drag
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Update positions on each tick of the simulation
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
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

    // Event Handlers
    
    // Auto-resize textarea as user types
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
        
        // Typing indicator
        fetch('/api/typing', { method: 'POST' });
        showTypingIndicator();
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(hideTypingIndicator, 2000);
    });
    
    // Handle message input
    messageInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const content = messageInput.value.trim();
            if (content) {
                messageInput.value = '';
                messageInput.style.height = 'auto';
                await sendMessage(content);
                
                // Update stats
                let messageCount = parseInt(messagesCountElement.textContent) || 0;
                messagesCountElement.textContent = messageCount + 1;
            }
        }
    });
    
    // Send button click handler
    sendButton.addEventListener('click', async () => {
        const content = messageInput.value.trim();
        if (content) {
            messageInput.value = '';
            messageInput.style.height = 'auto';
            await sendMessage(content);
            
            // Update stats
            let messageCount = parseInt(messagesCountElement.textContent) || 0;
            messagesCountElement.textContent = messageCount + 1;
        }
    });
    
    // Toggle left sidebar
    menuToggle.addEventListener('click', () => {
        appContainer.classList.toggle('sidebar-collapsed');
    });
    
    // Toggle theme
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        
        if (document.body.classList.contains('light-theme')) {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        }
    });
    
    // Mode switching
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all mode buttons
            modeBtns.forEach(b => b.classList.remove('active'));
            
            // Add active class to clicked button
            btn.classList.add('active');
            
            const mode = btn.dataset.mode;
            
            if (mode === 'workflow') {
                workflowDiagram.style.display = 'flex';
                chatArea.style.display = 'none';
            } else if (mode === 'chat') {
                workflowDiagram.style.display = 'none';
                chatArea.style.display = 'flex';
            } else if (mode === 'settings') {
                settingsModal.classList.add('active');
            }
        });
    });
    
    // Quick prompts
    quickPrompts.forEach(chip => {
        chip.addEventListener('click', () => {
            messageInput.value = chip.textContent;
            messageInput.focus();
        });
    });
    
    // Node filters
    nodeFilters.forEach(filter => {
        filter.addEventListener('click', () => {
            // Remove active class from all filters
            nodeFilters.forEach(f => f.classList.remove('active'));
            
            // Add active class to clicked filter
            filter.classList.add('active');
            
            const filterType = filter.dataset.filter;
            const nodes = document.querySelectorAll('.user');
            
            nodes.forEach(node => {
                if (filterType === 'all') {
                    node.style.display = 'flex';
                } else if (filterType === 'master' && node.querySelector('.user-name').textContent.includes('Scrum Master')) {
                    node.style.display = 'flex';
                } else if (filterType === 'active' && node.querySelector('.user-status').textContent.includes('Active')) {
                    node.style.display = 'flex';
                } else {
                    node.style.display = 'none';
                }
            });
        });
    });
    
    // Refresh nodes button
    refreshNodesBtn.addEventListener('click', async () => {
        refreshNodesBtn.classList.add('loading');
        await fetchInstances();
        setTimeout(() => {
            refreshNodesBtn.classList.remove('loading');
        }, 500);
    });
    
    // Formatting buttons
    formatButtons.forEach(button => {
        button.addEventListener('click', () => {
            const formatType = button.title.toLowerCase();
            const selectionStart = messageInput.selectionStart;
            const selectionEnd = messageInput.selectionEnd;
            const selectedText = messageInput.value.substring(selectionStart, selectionEnd);
            
            let formattedText = '';
            
            switch (formatType) {
                case 'bold':
                    formattedText = `**${selectedText}**`;
                    break;
                case 'italic':
                    formattedText = `*${selectedText}*`;
                    break;
                case 'code':
                    formattedText = selectedText.includes('\n') ? 
                        `\`\`\`\n${selectedText}\n\`\`\`` : 
                        `\`${selectedText}\``;
                    break;
                case 'link':
                    formattedText = `[${selectedText}](url)`;
                    break;
                case 'list':
                    formattedText = selectedText.split('\n').map(line => `- ${line}`).join('\n');
                    break;
            }
            
            // Replace the selected text with the formatted text
            messageInput.value = 
                messageInput.value.substring(0, selectionStart) + 
                formattedText + 
                messageInput.value.substring(selectionEnd);
                
            // Focus back on the textarea
            messageInput.focus();
        });
    });
    
    // Close modal
    closeModalBtn.addEventListener('click', () => {
        settingsModal.classList.remove('active');
        // Switch to chat mode when closing settings
        modeBtns.forEach(btn => {
            if (btn.dataset.mode === 'chat') {
                btn.click();
            }
        });
    });
    
    // Export conversation
    exportBtn.addEventListener('click', () => {
        const messages = JSON.parse(localStorage.getItem('chatMessages')) || [];
        
        // Create a formatted string with all messages
        const formattedMessages = messages.map(msg => {
            if (msg.role === 'user') {
                return `USER: ${msg.content}\n\n`;
            } else if (msg.error) {
                return `ERROR: ${msg.error}\n\n`;
            } else {
                return `${msg.role.toUpperCase()}: ${msg.content}\n\n`;
            }
        }).join('');
        
        // Create a Blob with the text
        const blob = new Blob([formattedMessages], { type: 'text/plain' });
        
        // Create a download link and trigger the download
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `gemini-conversation-${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
        
        // Show success toast
        showToast('Conversation exported successfully!', 'success');
    });
    
    // Share conversation (copy link)
    shareBtn.addEventListener('click', () => {
        // For simplicity, we'll just copy the current URL
        navigator.clipboard.writeText(window.location.href)
            .then(() => {
                showToast('Link copied to clipboard!', 'success');
            })
            .catch(() => {
                showToast('Failed to copy link', 'error');
            });
    });
    
    // File upload button click handler
    uploadFileBtn.addEventListener('click', () => {
        fileUploadInput.click();
    });
    
    // File input change handler
    fileUploadInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            
            // Check file type
            const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
            if (!validTypes.includes(file.type)) {
                showErrorToast('Invalid file type. Please upload a PNG, JPG, or GIF image.');
                return;
            }
            
            // Check file size (max 16MB)
            if (file.size > 16 * 1024 * 1024) {
                showErrorToast('File too large. Maximum size is 16MB.');
                return;
            }
            
            // Show loading spinner
            showLoadingSpinner();
            
            // Create FormData object
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                // Upload file
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Failed to upload file');
                }
                
                const data = await response.json();
                
                // Store uploaded file info
                currentUploadedFile = {
                    url: data.url,
                    filename: data.filename
                };
                
                // Show success message
                showToast(`File uploaded successfully: ${file.name}`, 'success');
                
                // Add image preview to message input
                const previewDiv = document.createElement('div');
                previewDiv.className = 'image-preview';
                previewDiv.innerHTML = `
                    <img src="${data.url}" alt="Uploaded image">
                    <span class="image-filename">${file.name}</span>
                    <button class="remove-image"><i class="fas fa-times"></i></button>
                `;
                
                // Add preview before the message input
                const messageInputContainer = document.querySelector('.message-input');
                messageInputContainer.parentNode.insertBefore(previewDiv, messageInputContainer);
                
                // Add event listener to remove button
                previewDiv.querySelector('.remove-image').addEventListener('click', () => {
                    previewDiv.remove();
                    currentUploadedFile = null;
                });
                
            } catch (error) {
                console.error('Error uploading file:', error);
                showErrorToast(error.message || 'Failed to upload file');
            } finally {
                hideLoadingSpinner();
            }
        }
    });
    
    // Drag and drop functionality
    const dropArea = document.querySelector('.chat-area');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });
    
    dropArea.addEventListener('dragenter', () => {
        dropArea.classList.add('drag-active');
    });
    
    dropArea.addEventListener('dragleave', () => {
        dropArea.classList.remove('drag-active');
    });
    
    dropArea.addEventListener('drop', async (e) => {
        dropArea.classList.remove('drag-active');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            
            // Check file type
            const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
            if (!validTypes.includes(file.type)) {
                showErrorToast('Invalid file type. Please upload a PNG, JPG, or GIF image.');
                return;
            }
            
            // Check file size (max 16MB)
            if (file.size > 16 * 1024 * 1024) {
                showErrorToast('File too large. Maximum size is 16MB.');
                return;
            }
            
            // Show loading spinner
            showLoadingSpinner();
            
            // Create FormData object
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                // Upload file
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Failed to upload file');
                }
                
                const data = await response.json();
                
                // Store uploaded file info
                currentUploadedFile = {
                    url: data.url,
                    filename: data.filename
                };
                
                // Show success message
                showToast(`File uploaded successfully: ${file.name}`, 'success');
                
                // Add image preview to message input
                const previewDiv = document.createElement('div');
                previewDiv.className = 'image-preview';
                previewDiv.innerHTML = `
                    <img src="${data.url}" alt="Uploaded image">
                    <span class="image-filename">${file.name}</span>
                    <button class="remove-image"><i class="fas fa-times"></i></button>
                `;
                
                // Add preview before the message input
                const messageInputContainer = document.querySelector('.message-input');
                messageInputContainer.parentNode.insertBefore(previewDiv, messageInputContainer);
                
                // Add event listener to remove button
                previewDiv.querySelector('.remove-image').addEventListener('click', () => {
                    previewDiv.remove();
                    currentUploadedFile = null;
                });
                
            } catch (error) {
                console.error('Error uploading file:', error);
                showErrorToast(error.message || 'Failed to upload file');
            } finally {
                hideLoadingSpinner();
            }
        }
    });
    
    // Modify sendMessage function to include image if available
    async function sendMessage(content) {
        if (!content.trim() && !currentUploadedFile) return;

        showLoadingSpinner();
        
        const userMessageElement = createMessageElement({
            role: 'user',
            content: content
        });
        addMessageWithAnimation(userMessageElement, { role: 'user', content: content });

        try {
            const requestBody = {
                message: content
            };
            
            // Add image info if available
            if (currentUploadedFile) {
                requestBody.image_attached = true;
            }
            
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
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
            
            // Clear image preview if exists
            const imagePreview = document.querySelector('.image-preview');
            if (imagePreview) {
                imagePreview.remove();
                currentUploadedFile = null;
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
    
    // Handle clear button click
    clearButton.addEventListener('click', clearAll);
    
    // Initial setup
    fetchInstances();
    
    // Update last updated time
    function updateLastUpdated() {
        lastUpdatedElement.textContent = 'Just now';
        setTimeout(() => {
            lastUpdatedElement.textContent = '1 minute ago';
        }, 60000);
    }
    
    // Periodically update instances every 10 seconds
    setInterval(() => {
        fetchInstances();
        updateLastUpdated();
    }, 10000);
    
    // Set initial stats
    messagesCountElement.textContent = (JSON.parse(localStorage.getItem('chatMessages')) || []).length;
    apiCallsElement.textContent = '0';
    updateLastUpdated();
    
    // Initialize auto-height for textarea
    messageInput.style.height = 'auto';
    
    // Add toast function to window for access throughout the app
    window.showAppToast = showToast;
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

// Updated toast function with type parameter
function showToast(message, type = 'error') {
    // Remove any existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    // Create the new toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Add icon based on type
    let icon = '';
    switch(type) {
        case 'success':
            icon = '<i class="fas fa-check-circle"></i>';
            break;
        case 'error':
            icon = '<i class="fas fa-exclamation-circle"></i>';
            break;
        case 'warning':
            icon = '<i class="fas fa-exclamation-triangle"></i>';
            break;
        case 'info':
            icon = '<i class="fas fa-info-circle"></i>';
            break;
    }
    
    toast.innerHTML = `${icon}<span>${message}</span>`;
    document.body.appendChild(toast);

    // Show the toast with a slight delay for animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    // Hide and remove the toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Keep the old function for backward compatibility
function showErrorToast(message) {
    showToast(message, 'error');
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
