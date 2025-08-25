// frontend/src/services/api.js

const API_URL = process.env.REACT_APP_API_URL || 'https://api.badge.iopn.io';

// Helper function for API calls
const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `API call failed: ${response.statusText}`);
  }

  return response.json();
};

export const authService = {
  // Twitter OAuth
  async getTwitterLoginUrl(email = '', referralCode = '') {
    const params = new URLSearchParams();
    if (email) params.append('email', email);
    if (referralCode) params.append('ref', referralCode);
    const queryString = params.toString();
    return apiCall(`/auth/twitter/login${queryString ? '?' + queryString : ''}`);
  },

  // Discord OAuth
  getDiscordLoginUrl(email = '', referralCode = '') {
    const params = new URLSearchParams();
    if (email) params.append('email', email);
    if (referralCode) params.append('ref', referralCode);
    const queryString = params.toString();
    return `${API_URL}/auth/discord/login${queryString ? '?' + queryString : ''}`;
  },

  // Email registration (legacy - use sendVerificationCode or registerInstant instead)
  async registerEmail(email, referralCode = null) {
    return apiCall('/auth/email/register', {
      method: 'POST',
      body: JSON.stringify({ email, referral_code: referralCode }),
    });
  },

  // Send verification code (for existing users)
  async sendVerificationCode(email, referralCode = null) {
    return apiCall('/auth/email/send-verification', {
      method: 'POST',
      body: JSON.stringify({ email, referral_code: referralCode }),
    });
  },

  // Verify code
  async verifyCode(email, code) {
    return apiCall('/auth/email/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    });
  },

  // Register instant (for new users who haven't registered yet)
  async registerInstant(email, referralCode = null) {
    return apiCall('/auth/email/register-instant', {
      method: 'POST',
      body: JSON.stringify({ email, referral_code: referralCode }),
    });
  },

  // Check email status (using the /auth/email/status endpoint)
  async checkEmailStatus(email) {
    return apiCall(`/auth/email/status/${encodeURIComponent(email)}`);
  },

  // Check user status (using the main /api/status endpoint)
  async checkUserStatus(email) {
    return apiCall(`/api/status/${encodeURIComponent(email)}`);
  },

  // Get user dashboard
  async getUserDashboard(email) {
    return apiCall(`/api/dashboard/${encodeURIComponent(email)}`);
  },

  // Claim badge with referral
  async claimBadge(email, referralCode = null) {
    return apiCall('/api/claim-badge-with-referral', {
      method: 'POST',
      body: JSON.stringify({ email, referral_code: referralCode }),
    });
  },

  // Telegram verification
  async verifyTelegram(telegramId) {
    return apiCall(`/auth/telegram/verify/${telegramId}`);
  },

  // Link Telegram to email account
  async linkTelegram(email, telegramId, telegramUsername = '') {
    return apiCall('/auth/telegram/link-simple', {
      method: 'POST',
      body: JSON.stringify({ 
        email, 
        telegram_id: String(telegramId), 
        telegram_username: telegramUsername 
      }),
    });
  },

  // Link Telegram and Twitter accounts (legacy)
  async linkAccounts(telegramId, twitterId) {
    return apiCall('/auth/telegram/link-account', {
      method: 'POST',
      body: JSON.stringify({ telegram_id: telegramId, twitter_id: twitterId }),
    });
  },

  // Check badge status
  async checkBadgeStatus(platform, userId) {
    switch (platform) {
      case 'telegram':
        return apiCall(`/auth/telegram/badge/status/${userId}`);
      case 'discord':
        return apiCall(`/status/${userId}`);
      case 'twitter':
        return apiCall(`/auth/twitter/status/${userId}`);
      case 'email':
        return apiCall(`/auth/email/status/${encodeURIComponent(userId)}`);
      default:
        throw new Error('Invalid platform');
    }
  },

  // Issue badge
  async issueBadge(data) {
    return apiCall('/auth/telegram/badge/issue', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Get Telegram bot URL
  getTelegramBotUrl(email = '', referralCode = '') {
    const botUsername = process.env.REACT_APP_TELEGRAM_BOT_USERNAME || 'IOPnBadgeBot';
    let startParam = '';
    
    if (email || referralCode) {
      // Create base64 encoded parameter
      const data = referralCode ? `${email}|${referralCode}` : email;
      startParam = `?start=verify_${btoa(data).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')}`;
    }
    
    return `https://t.me/${botUsername}${startParam}`;
  },
};

// Handle OAuth callbacks
export const handleOAuthCallback = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const auth = urlParams.get('auth');
  const status = urlParams.get('status');
  const platform = urlParams.get('platform');
  const username = urlParams.get('username');
  const message = urlParams.get('message');
  const referralCode = urlParams.get('ref');
  
  if ((auth && status) || (platform && status)) {
    return { 
      platform: platform || auth, 
      status,
      username,
      message,
      referralCode
    };
  }
  
  return null;
};