/**
 * Fuzzy Waffle OCR Chatbot Widget
 * 
 * Provides intelligent assistance during invoice processing
 * Integrates with existing Raven ChatGPT credentials
 */

class FuzzyWaffleChatbot {
    constructor() {
        this.isInitialized = false;
        this.conversationId = null;
        this.isVisible = false;
        this.context = {};
        
        this.init();
    }
    
    init() {
        // Check if assistant is enabled
        this.checkAssistantStatus().then(status => {
            if (status.enabled) {
                this.createChatWidget();
                this.bindEvents();
                this.isInitialized = true;
                
                console.log('🤖 Fuzzy Waffle Assistant initialized');
                console.log(`📡 Using ${status.source} credentials with ${status.model}`);
            }
        });
    }
    
    async checkAssistantStatus() {
        try {
            const response = await frappe.call({
                method: 'fuzzy_waffle_ocr.ai_integration.chatbot_assistant.check_assistant_status'
            });
            return response.message;
        } catch (error) {
            console.error('Failed to check assistant status:', error);
            return { enabled: false };
        }
    }
    
    createChatWidget() {
        // Create floating chat button
        const chatButton = $(`
            <div id="fuzzy-chat-button" class="fuzzy-chat-btn" title="OCR Assistant">
                <i class="fa fa-robot"></i>
                <span class="chat-badge" style="display: none;">!</span>
            </div>
        `);
        
        // Create chat window
        const chatWindow = $(`
            <div id="fuzzy-chat-window" class="fuzzy-chat-window" style="display: none;">
                <div class="chat-header">
                    <div class="chat-title">
                        <i class="fa fa-robot"></i>
                        <span>Fuzzy Waffle Assistant</span>
                    </div>
                    <div class="chat-controls">
                        <button class="btn-minimize" title="Minimize">−</button>
                        <button class="btn-close" title="Close">×</button>
                    </div>
                </div>
                
                <div class="chat-messages" id="chat-messages">
                    <div class="welcome-message">
                        <div class="message assistant-message">
                            <div class="message-content">
                                Hello! I'm your Fuzzy Waffle OCR assistant. I can help you with:
                                <ul>
                                    <li>📄 Invoice processing questions</li>
                                    <li>🧠 Explaining OCR results</li>
                                    <li>💰 Expense head categorization</li>
                                    <li>🔄 UOM conversions</li>
                                    <li>📈 Improving automation accuracy</li>
                                </ul>
                                How can I assist you today?
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quick-actions" id="quick-actions">
                    <button class="quick-btn" data-action="low_accuracy">🎯 Improve OCR Accuracy</button>
                    <button class="quick-btn" data-action="handwriting">✍️ Handwriting Help</button>
                    <button class="quick-btn" data-action="expense_heads">💰 Expense Categories</button>
                    <button class="quick-btn" data-action="uom_conversion">🔄 UOM Conversions</button>
                </div>
                
                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <textarea id="chat-input" placeholder="Ask me anything about invoice processing..." rows="1"></textarea>
                        <button id="send-message" class="btn-send" disabled>
                            <i class="fa fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
                
                <div class="chat-status" id="chat-status" style="display: none;">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                    Assistant is typing...
                </div>
            </div>
        `);
        
        // Add CSS styles
        this.addChatStyles();
        
        // Append to body
        $('body').append(chatButton, chatWindow);
    }
    
    addChatStyles() {
        const styles = `
            <style>
                .fuzzy-chat-btn {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    width: 60px;
                    height: 60px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
                    transition: all 0.3s ease;
                    z-index: 1000;
                }
                
                .fuzzy-chat-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
                }
                
                .fuzzy-chat-btn .chat-badge {
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background: #ff4757;
                    color: white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                }
                
                .fuzzy-chat-window {
                    position: fixed;
                    bottom: 100px;
                    right: 20px;
                    width: 380px;
                    height: 600px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                    display: flex;
                    flex-direction: column;
                    z-index: 1001;
                    border: 1px solid #e0e6ed;
                }
                
                .chat-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px 20px;
                    border-radius: 12px 12px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .chat-title {
                    display: flex;
                    align-items: center;
                    font-weight: 600;
                    gap: 8px;
                }
                
                .chat-controls {
                    display: flex;
                    gap: 8px;
                }
                
                .chat-controls button {
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    background: #f8f9fa;
                }
                
                .message {
                    margin-bottom: 16px;
                    animation: messageSlideIn 0.3s ease;
                }
                
                .assistant-message .message-content {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 12px 12px 12px 4px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    max-width: 85%;
                }
                
                .user-message {
                    text-align: right;
                }
                
                .user-message .message-content {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 16px;
                    border-radius: 12px 12px 4px 12px;
                    display: inline-block;
                    max-width: 85%;
                }
                
                .quick-actions {
                    padding: 12px 16px;
                    border-top: 1px solid #e0e6ed;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    background: white;
                }
                
                .quick-btn {
                    background: #f1f3f4;
                    border: 1px solid #dadce0;
                    color: #3c4043;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .quick-btn:hover {
                    background: #e8eaed;
                    transform: translateY(-1px);
                }
                
                .chat-input-container {
                    border-top: 1px solid #e0e6ed;
                    padding: 16px;
                    background: white;
                    border-radius: 0 0 12px 12px;
                }
                
                .chat-input-wrapper {
                    display: flex;
                    gap: 8px;
                    align-items: flex-end;
                }
                
                #chat-input {
                    flex: 1;
                    border: 1px solid #dadce0;
                    border-radius: 20px;
                    padding: 8px 16px;
                    resize: none;
                    max-height: 100px;
                    font-family: inherit;
                    outline: none;
                }
                
                #chat-input:focus {
                    border-color: #667eea;
                    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
                }
                
                .btn-send {
                    width: 36px;
                    height: 36px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    border-radius: 50%;
                    color: white;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s ease;
                }
                
                .btn-send:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                
                .btn-send:not(:disabled):hover {
                    transform: scale(1.05);
                }
                
                .chat-status {
                    padding: 8px 16px;
                    background: #f8f9fa;
                    border-top: 1px solid #e0e6ed;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 12px;
                    color: #666;
                }
                
                .typing-indicator {
                    display: flex;
                    gap: 2px;
                }
                
                .typing-indicator span {
                    width: 4px;
                    height: 4px;
                    background: #667eea;
                    border-radius: 50%;
                    animation: typing 1.4s infinite ease-in-out;
                }
                
                .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
                .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
                
                @keyframes typing {
                    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
                    40% { transform: scale(1.2); opacity: 1; }
                }
                
                @keyframes messageSlideIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @media (max-width: 480px) {
                    .fuzzy-chat-window {
                        width: calc(100% - 40px);
                        height: calc(100% - 140px);
                        bottom: 20px;
                        right: 20px;
                        left: 20px;
                    }
                }
            </style>
        `;
        $('head').append(styles);
    }
    
    bindEvents() {
        const chatButton = $('#fuzzy-chat-button');
        const chatWindow = $('#fuzzy-chat-window');
        const chatInput = $('#chat-input');
        const sendButton = $('#send-message');
        
        // Toggle chat window
        chatButton.on('click', () => {
            this.toggleChat();
        });
        
        // Close/minimize buttons
        chatWindow.find('.btn-close').on('click', () => {
            this.hideChat();
        });
        
        chatWindow.find('.btn-minimize').on('click', () => {
            this.toggleChat();
        });
        
        // Quick action buttons
        $('.quick-btn').on('click', (e) => {
            const action = $(e.target).data('action');
            this.handleQuickAction(action);
        });
        
        // Chat input handling
        chatInput.on('input', () => {
            const hasText = chatInput.val().trim().length > 0;
            sendButton.prop('disabled', !hasText);
            
            // Auto-resize textarea
            chatInput[0].style.height = 'auto';
            chatInput[0].style.height = chatInput[0].scrollHeight + 'px';
        });
        
        chatInput.on('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        sendButton.on('click', () => {
            this.sendMessage();
        });
    }
    
    toggleChat() {
        const chatWindow = $('#fuzzy-chat-window');
        this.isVisible = !this.isVisible;
        
        if (this.isVisible) {
            chatWindow.show();
            $('#chat-input').focus();
        } else {
            chatWindow.hide();
        }
    }
    
    showChat() {
        $('#fuzzy-chat-window').show();
        $('#chat-input').focus();
        this.isVisible = true;
    }
    
    hideChat() {
        $('#fuzzy-chat-window').hide();
        this.isVisible = false;
    }
    
    setContext(context) {
        this.context = { ...this.context, ...context };
        
        // Show notification badge if context suggests help might be needed
        if (context.ocr_confidence < 70) {
            $('#fuzzy-chat-button .chat-badge').show();
        }
    }
    
    async handleQuickAction(action) {
        try {
            this.showTyping();
            
            const response = await frappe.call({
                method: 'fuzzy_waffle_ocr.ai_integration.chatbot_assistant.get_ocr_help',
                args: {
                    issue_type: action,
                    context: JSON.stringify(this.context)
                }
            });
            
            this.hideTyping();
            this.addAssistantMessage(response.message.response);
            
        } catch (error) {
            this.hideTyping();
            this.addAssistantMessage('Sorry, I encountered an error. Please try again.');
            console.error('Quick action error:', error);
        }
    }
    
    async sendMessage() {
        const chatInput = $('#chat-input');
        const message = chatInput.val().trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addUserMessage(message);
        chatInput.val('').trigger('input');
        
        try {
            this.showTyping();
            
            // Generate conversation ID if not exists
            if (!this.conversationId) {
                this.conversationId = frappe.utils.get_random(8);
            }
            
            const response = await frappe.call({
                method: 'fuzzy_waffle_ocr.ai_integration.chatbot_assistant.chat_with_assistant',
                args: {
                    message: message,
                    context: JSON.stringify({
                        ...this.context,
                        conversation_id: this.conversationId
                    })
                }
            });
            
            this.hideTyping();
            this.addAssistantMessage(response.message.response);
            
        } catch (error) {
            this.hideTyping();
            this.addAssistantMessage('Sorry, I encountered an error. Please try again.');
            console.error('Chat error:', error);
        }
    }
    
    addUserMessage(message) {
        const messagesContainer = $('#chat-messages');
        const messageHtml = `
            <div class="message user-message">
                <div class="message-content">${frappe.utils.escape_html(message)}</div>
            </div>
        `;
        messagesContainer.append(messageHtml);
        this.scrollToBottom();
    }
    
    addAssistantMessage(message) {
        const messagesContainer = $('#chat-messages');
        const messageHtml = `
            <div class="message assistant-message">
                <div class="message-content">${this.formatAssistantMessage(message)}</div>
            </div>
        `;
        messagesContainer.append(messageHtml);
        this.scrollToBottom();
    }
    
    formatAssistantMessage(message) {
        // Convert markdown-like formatting to HTML
        message = frappe.utils.escape_html(message);
        message = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        message = message.replace(/\*(.*?)\*/g, '<em>$1</em>');
        message = message.replace(/\n/g, '<br>');
        
        // Convert lists
        message = message.replace(/^\- (.+)$/gm, '<li>$1</li>');
        if (message.includes('<li>')) {
            message = message.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        return message;
    }
    
    showTyping() {
        $('#chat-status').show();
        $('#quick-actions').hide();
        this.scrollToBottom();
    }
    
    hideTyping() {
        $('#chat-status').hide();
        $('#quick-actions').show();
    }
    
    scrollToBottom() {
        const messagesContainer = $('#chat-messages')[0];
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Public API methods
    static getInstance() {
        if (!window.fuzzyWaffleChatbot) {
            window.fuzzyWaffleChatbot = new FuzzyWaffleChatbot();
        }
        return window.fuzzyWaffleChatbot;
    }
    
    static setContext(context) {
        const instance = FuzzyWaffleChatbot.getInstance();
        instance.setContext(context);
    }
    
    static showHelp(topic) {
        const instance = FuzzyWaffleChatbot.getInstance();
        instance.showChat();
        instance.handleQuickAction(topic);
    }
}

// Initialize on page load
$(document).ready(() => {
    // Only initialize on relevant pages
    const relevantPages = [
        'purchase-invoice', 
        'journal-entry', 
        'invoice-ocr-processor',
        'supplier-item-mapping'
    ];
    
    const currentPage = frappe.get_route_str();
    
    if (relevantPages.some(page => currentPage.includes(page))) {
        FuzzyWaffleChatbot.getInstance();
    }
});

// Export for global access
window.FuzzyWaffleChatbot = FuzzyWaffleChatbot;