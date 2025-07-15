// frontend/src/services/api.js

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
    throw new Error(`API call failed: ${response.statusText}`);
  }

  return response.json();
};

export const authService = {
  // Twitter OAuth
  async getTwitterLoginUrl() {
    return apiCall('/auth/twitter/login');
  },

  // Discord OAuth
  getDiscordLoginUrl() {
    const clientId = process.env.REACT_APP_DISCORD_CLIENT_ID;
    const redirectUri = encodeURIComponent(`${API_URL}/auth/discord/callback`);
    return `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=identify%20guilds`;
  },

  // Email registration
  async registerEmail(email) {
    return apiCall('/auth/email/register', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  // Check email status
  async checkEmailStatus(email) {
    return apiCall(`/auth/email/status/${encodeURIComponent(email)}`);
  },

  // Telegram verification
  async verifyTelegram(telegramId) {
    return apiCall(`/auth/telegram/verify/${telegramId}`);
  },

  // Link Telegram and Twitter accounts
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
};

// Handle OAuth callbacks
export const handleOAuthCallback = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const auth = urlParams.get('auth');
  const status = urlParams.get('status');
  
  if (auth && status) {
    return { platform: auth, status };
  }
  
  return null;
};