/**
 * Mage Data Chatbot Configuration
 * Replace src/utils/chatbot.ts with this file.
 */

export const chatbotConfig = {
  enabled: true,

  // Backend API endpoint — update this to your deployed backend URL
  apiEndpoint: 'https://your-api-domain.com/api/chat',
  // For same-origin proxy during development: '/api/chat'

  // Deferred loading: load chatbot JS after this many ms of idle
  delayMs: 5000,

  // Lead capture settings (Section 7)
  leadCapture: {
    enabled: true,
    triggerAfterMessages: 3,
    hubspotPortalId: 'HUBSPOT_PORTAL_ID',   // from src/utils/hubspot.ts
    hubspotFormId: 'HUBSPOT_FORM_ID',
  },

  // UI copy and strings (Section 3e)
  ui: {
    title: 'Mage Data Assistant',
    welcomeMessage: "Hi! I'm the Mage Data assistant. How can I help you today?",
    quickReplies: ['Request a demo', 'Learn about products', 'Talk to sales'],
    placeholder: 'Type a message...',
    errorMessage: "Sorry, I'm having trouble connecting. Please try again or contact info@magedata.ai",
  },

  // Brand colors (Section 3a)
  colors: {
    navy: '#122045',
    orange: '#E67425',
    orangeHover: '#CF6620',
    white: '#FFFFFF',
    grayBg: '#F0F2F4',
    grayLight: '#F8F9FA',
    grayText: '#6B7280',
  },
};
