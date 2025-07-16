import React, { useState, useEffect } from 'react';
import { Check, Twitter, MessageCircle, AlertCircle, Users, Link2, Mail, Loader2, ArrowRight, Copy, Download, Share2, ExternalLink, ArrowLeft, X, CheckCircle, Info, TrendingUp } from 'lucide-react';
import UserDashboard from './UserDashboard';

// Custom Notification Component
const Notification = ({ type, title, message, isVisible, onClose }) => {
  useEffect(() => {
    if (isVisible && onClose) {
      const timer = setTimeout(onClose, 5000); // Auto-close after 5 seconds
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  const styles = {
    success: {
      bg: 'bg-green-900/20',
      border: 'border-green-600/50',
      icon: <CheckCircle className="w-5 h-5 text-green-400" />,
      titleColor: 'text-green-400',
      textColor: 'text-green-300'
    },
    error: {
      bg: 'bg-red-900/20',
      border: 'border-red-600/50',
      icon: <AlertCircle className="w-5 h-5 text-red-400" />,
      titleColor: 'text-red-400',
      textColor: 'text-red-300'
    },
    info: {
      bg: 'bg-blue-900/20',
      border: 'border-blue-600/50',
      icon: <Info className="w-5 h-5 text-blue-400" />,
      titleColor: 'text-blue-400',
      textColor: 'text-blue-300'
    }
  };

  const style = styles[type] || styles.info;

  return (
    <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
      <div className={`${style.bg} ${style.border} border rounded-xl p-4 backdrop-blur-lg shadow-2xl max-w-sm`}>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">{style.icon}</div>
          <div className="flex-1">
            <h4 className={`font-semibold ${style.titleColor} mb-1`}>{title}</h4>
            {message && <p className={`text-sm ${style.textColor}`}>{message}</p>}
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Progress Indicator Component - Simplified
const ProgressIndicator = ({ currentStep, totalSteps, completedTasks }) => {
  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-40">
      <div className="bg-black/60 backdrop-blur-md rounded-full px-6 py-3 border border-gray-800 flex items-center gap-4">
        {/* Progress dots */}
        <div className="flex items-center gap-2">
          {[0, 1, 2, 3].map((index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                index < completedTasks 
                  ? 'bg-green-400' 
                  : 'bg-gray-600'
              }`}
            />
          ))}
        </div>
        
        {/* Divider */}
        <div className="w-px h-4 bg-gray-700" />
        
        {/* Current step label */}
        <span className="text-xs text-gray-400">
          Step {completedTasks + 1} of 4
        </span>
      </div>
    </div>
  );
};

const SocialDashboard = () => {
  const [currentStep, setCurrentStep] = useState('welcome'); 
  const [email, setEmail] = useState('');
  const [emailInput, setEmailInput] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [discordAttempted, setDiscordAttempted] = useState(false);
  const [discordInviteLink, setDiscordInviteLink] = useState('');
  const [referralCode, setReferralCode] = useState('');
  const [userReferralCode, setUserReferralCode] = useState('');
  const [isReturningUser, setIsReturningUser] = useState(false);

  const [tasks, setTasks] = useState({
    email: false,
    twitter: false,
    telegram: false,
    discord: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const referralLink = userReferralCode ? `https://badge.iopn.io/?ref=${userReferralCode}`: `https://badge.iopn.io`;

  const [copiedText, setCopiedText] = useState('');
  const [showBadgeAnimation, setShowBadgeAnimation] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);
  const [twitterAttempted, setTwitterAttempted] = useState(false);

  
  // Notification state
  const [notification, setNotification] = useState({
    isVisible: false,
    type: 'info',
    title: '',
    message: ''
  });

  const API_URL = process.env.REACT_APP_API_URL || 'https://api.badge.iopn.io';
  const TELEGRAM_BOT_USERNAME = process.env.REACT_APP_TELEGRAM_BOT_USERNAME || 'iopn_badge_bot';

  const completedTasks = Object.values(tasks).filter(Boolean).length;
  const totalTasks = 4;

  // Show notification helper
  const showNotification = (type, title, message) => {
    setNotification({
      isVisible: true,
      type,
      title,
      message
    });
  };

  // Timer for resend code
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Check status function
  const checkStatus = async (emailToCheck = null) => {
    const userEmail = emailToCheck || email || localStorage.getItem('userEmail');
    if (!userEmail) return;

    try {
      const response = await fetch(`${API_URL}/api/status/${encodeURIComponent(userEmail)}`);
      const data = await response.json();
      
      if (data.exists && data.tasks) {
        setTasks(data.tasks);
        setEmail(userEmail);
        
        // Fetch user's referral code if they have one
        try {
          const dashResponse = await fetch(`${API_URL}/api/dashboard/${encodeURIComponent(userEmail)}`);
          if (dashResponse.ok) {
            const dashData = await dashResponse.json();
            setUserReferralCode(dashData.user.referral_code);
          }
        } catch (err) {
          console.error('Error fetching referral code:', err);
        }
        
        // If badge is already issued, show dashboard
        if (data.badge_issued) {
          setCurrentStep('dashboard');
        } else if (!data.tasks.email) {
          setCurrentStep('email');
        } else if (!data.tasks.twitter) {
          setCurrentStep('twitter');
        } else if (!data.tasks.telegram) {
          setCurrentStep('telegram');
        } else if (!data.tasks.discord) {
          setCurrentStep('discord');
        } else {
          setCurrentStep('summary');
        }
        
        return data;
      }
      
      return null;
    } catch (error) {
      console.error('Error checking status:', error);
      return null;
    }
  };

  // Check OAuth callbacks
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const platform = urlParams.get('platform');
    const status = urlParams.get('status');
    const message = urlParams.get('message');
    const username = urlParams.get('username');
    const invite = urlParams.get('invite');
    const savedEmail = localStorage.getItem('userEmail');

    if (platform && status && savedEmail) {
      setEmail(savedEmail);
      
      if (status === 'success') {
        // Handle success
        setTasks(prev => ({ ...prev, [platform]: true }));
        
        // Show success notification
        if (username) {
          showNotification(
            'success',
            `${platform.charAt(0).toUpperCase() + platform.slice(1)} Connected!`,
            `@${username} connected successfully`
          );
        } else {
          showNotification('success', 'Connected!', `${platform} account connected successfully`);
        }
        
        // Navigate to next step
        if (platform === 'twitter') {
          setCurrentStep('telegram');
        } else if (platform === 'discord') {
          setCurrentStep('summary');
        }
      } else if (status === 'duplicate') {
        // Handle duplicate account error
        const decodedMessage = message ? decodeURIComponent(message) : 
          `This ${platform} account is already linked to another badge.`;
        
        showNotification('error', 'Account Already Used', decodedMessage);
        
        // Navigate back to the appropriate step
        if (platform === 'twitter') {
          setCurrentStep('twitter');
        } else if (platform === 'discord') {
          setCurrentStep('discord');
        }
      } else if (status === 'not_member') {
        // Handle Discord/Twitter not following/member
        if (platform === 'discord') {
          setDiscordAttempted(true);
          setDiscordInviteLink(invite || 'https://discord.gg/iopn');
          setCurrentStep('discord');
          
          const decodedMessage = message ? decodeURIComponent(message) : 
            'You need to join the IOPn Discord server first.';
          
          showNotification('error', 'Not a Member', decodedMessage);
        } else if (platform === 'twitter') {
          setTwitterAttempted(true);
          setCurrentStep('twitter');
          showNotification('error', 'Not Following', 'Please follow @IOPn_io on Twitter first');
        }
      } else if (status === 'error') {
        // Handle general errors
        const errorMessage = message 
          ? decodeURIComponent(message) 
          : 'An error occurred. Please try again.';
        
        showNotification('error', 'Error', errorMessage);
        
        // Navigate back to the appropriate step
        if (platform === 'twitter') {
          setCurrentStep('twitter');
        } else if (platform === 'discord') {
          setCurrentStep('discord');
        }
      }
      
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (savedEmail && !platform) {
      // If we have email but no OAuth callback, check status
      checkStatus();
    }
  }, []);

  // Check status on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem('userEmail');
    if (savedEmail) {
      setEmail(savedEmail);
      // Don't automatically check status on mount
      // Let user go through email verification for security
      setCurrentStep('email');
      setEmailInput(savedEmail); // Pre-fill the email input
    }
  }, []);

  // Badge animation
  useEffect(() => {
    if (currentStep === 'welcome') {
      setTimeout(() => setShowBadgeAnimation(true), 100);
    }
  }, [currentStep]);

  useEffect(() => {
    // Check for referral code in URL
    const urlParams = new URLSearchParams(window.location.search);
    const ref = urlParams.get('ref');
    if (ref) {
      setReferralCode(ref);
      localStorage.setItem('referralCode', ref);
    } else {
      // Check localStorage for saved referral code
      const savedRef = localStorage.getItem('referralCode');
      if (savedRef) {
        setReferralCode(savedRef);
      }
    }
  }, []);

  const handleSendVerificationCode = async () => {
    if (!emailInput || !emailInput.includes('@')) {
      showNotification('error', 'Invalid Email', 'Please enter a valid email address');
      return;
    }

    setIsLoading(true);
    try {
      // Check if user is returning
      const checkResponse = await fetch(`${API_URL}/api/status/${encodeURIComponent(emailInput)}`);
      if (checkResponse.ok) {
        const checkData = await checkResponse.json();
        if (checkData.exists) {
          setIsReturningUser(true);
        }
      }

      const response = await fetch(`${API_URL}/auth/email/send-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailInput })
      });

      if (response.ok) {
        setEmail(emailInput);
        setCurrentStep('email-verify');
        setResendTimer(60);
        showNotification('success', 'Code Sent!', 'Check your email for the verification code');
      } else {
        const error = await response.json();
        showNotification('error', 'Failed to Send Code', error.detail || 'Please try again');
      }
    } catch (error) {
      console.error('Send verification error:', error);
      showNotification('error', 'Network Error', 'Failed to connect. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      showNotification('error', 'Invalid Code', 'Please enter the 6-digit code');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/email/verify-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email: email,
          code: verificationCode 
        })
      });

      if (response.ok) {
        // Save email to localStorage
        localStorage.setItem('userEmail', email);
        
        // Check user status to determine where to send them
        showNotification('success', 'Email Verified!', 'Checking your progress...');
        
        // Wait a bit for the notification to show
        setTimeout(async () => {
          const status = await checkStatus(email);
          
          if (!status) {
            // New user - start from beginning
            setTasks(prev => ({ ...prev, email: true }));
            setCurrentStep('twitter');
          }
          // checkStatus will handle navigation based on their progress
        }, 1000);
        
      } else {
        const error = await response.json();
        showNotification('error', 'Verification Failed', error.detail || 'Invalid code. Please try again.');
      }
    } catch (error) {
      console.error('Verify code error:', error);
      showNotification('error', 'Network Error', 'Failed to verify. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTwitterAuth = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/twitter/login?email=${encodeURIComponent(email)}`);
      const data = await response.json();
      
      if (data.auth_url) {
        showNotification('info', 'Redirecting...', 'Taking you to Twitter');
        setTimeout(() => {
          window.location.href = data.auth_url;
        }, 1000);
      }
    } catch (error) {
      console.error('Twitter auth error:', error);
      showNotification('error', 'Connection Failed', 'Failed to connect to Twitter. Please try again.');
      setIsLoading(false);
    }
  };

  const handleTelegramAuth = () => {
  const refCode = referralCode || localStorage.getItem('referralCode') || '';
  // Encode email and referral code together
  const dataToEncode = refCode ? `${email}|${refCode}` : email;
  const encodedData = btoa(dataToEncode);
  const botUrl = `https://t.me/${TELEGRAM_BOT_USERNAME}?start=verify_${encodedData}`;
  
  console.log('Opening bot with URL:', botUrl);
  window.open(botUrl, '_blank');
  
  showNotification('info', 'Bot Opened', 'Complete verification in Telegram, then check status');
    
    // Start polling
    let attempts = 0;
    const maxAttempts = 40;
    
    const interval = setInterval(async () => {
      attempts++;
      console.log(`Polling attempt ${attempts}/${maxAttempts}`);
      
      try {
        const response = await fetch(`${API_URL}/api/status/${encodeURIComponent(email)}`);
        const data = await response.json();
        
        console.log('Poll response:', data);
        
        if (data.tasks && data.tasks.telegram) {
          console.log('Telegram verified! Updating UI...');
          setTasks(prev => ({ ...prev, telegram: true }));
          clearInterval(interval);
          showNotification('success', 'Telegram Verified!', 'Moving to Discord...');
          setTimeout(() => setCurrentStep('discord'), 1500);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
      
      if (attempts >= maxAttempts) {
        clearInterval(interval);
        console.log('Polling stopped after max attempts');
        checkStatus();
      }
    }, 3000);
  };

const handleDiscordAuth = async () => {
  setIsLoading(true);
  try {
    const refCode = referralCode || localStorage.getItem('referralCode') || '';
    const response = await fetch(`${API_URL}/auth/discord/login?email=${encodeURIComponent(email)}&ref=${encodeURIComponent(refCode)}`);
    const data = await response.json();
    
    if (data.auth_url) {
      showNotification('info', 'Redirecting...', 'Taking you to Discord');
      setTimeout(() => {
        window.location.href = data.auth_url;
      }, 1000);
    }
  } catch (error) {
    console.error('Discord login error:', error);
    showNotification('error', 'Connection Failed', 'Failed to connect to Discord. Please try again.');
    setIsLoading(false);
  }
};

  const handleClaim = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/claim-badge-with-referral`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email,
          referral_code: referralCode || localStorage.getItem('referralCode') || null
        })
      });

      const data = await response.json();
      if (data.success) {
        // Check if referrer got a drop
        if (data.referral_reward) {
          const drop = data.referral_reward.drop;
          showNotification(
            'info', 
            `Your referrer earned a ${drop.tier} drop!`,
            `They'll receive ${drop.rep_range.min}-${drop.rep_range.max} REP when Origin NFT launches`
          );
        }
        
        showNotification('success', 'Badge Claimed!', 'Congratulations! 🎉');
        
        // Fetch user's referral code for the claimed page
        try {
          const dashResponse = await fetch(`${API_URL}/api/dashboard/${encodeURIComponent(email)}`);
          if (dashResponse.ok) {
            const dashData = await dashResponse.json();
            setUserReferralCode(dashData.user.referral_code);
          }
        } catch (err) {
          console.error('Error fetching referral code:', err);
        }
        
        setTimeout(() => setCurrentStep('claimed'), 1500);
      } else {
        showNotification('error', 'Claim Failed', data.error || 'Please try again');
      }
    } catch (error) {
      console.error('Claim error:', error);
      showNotification('error', 'Network Error', 'Failed to claim badge. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    showNotification('success', 'Copied!', 'Link copied to clipboard');
    setTimeout(() => setCopiedText(''), 2000);
  };

  const shareOnTwitter = () => {
    const text = `I just claimed my Early n-Badge from @IOPn_io! 🚀\n\nJoin the identity revolution:\n${referralLink}`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
  };

  // Show progress indicator on all pages except welcome and claimed
  const showProgress = !['welcome', 'claimed', 'dashboard'].includes(currentStep);

  // Welcome Page
  if (currentStep === 'welcome') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="relative z-10 max-w-2xl w-full text-center">
          <img src={`${process.env.PUBLIC_URL}/logo.png`} alt="IOPn Logo" className="w-16 h-16 mb-4 mx-auto" />
          
          <h1 className="text-3xl md:text-4xl font-bold mb-3">Welcome to the sovereign stack.</h1>
          <p className="text-lg text-gray-300 mb-4">This is your first step toward the identity layer.</p>
          
          <p className="text-sm text-gray-400 mb-6 max-w-lg mx-auto">
            The Early n-Badge marks you as one of the first. One of the sovereign.
            Claiming it now will give you an edge during the upcoming Testnet.
          </p>

          <div className={`mb-6 transition-all duration-1200 ease-out ${
            showBadgeAnimation ? 'opacity-100 transform scale-100' : 'opacity-0 transform scale-90'
          }`}>
            <div className="relative w-40 h-40 mx-auto">
              <img 
                src={`${process.env.PUBLIC_URL}/badge.png`} 
                alt="Early n-Badge" 
                className="w-full h-full object-contain animate-pulse"
              />
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-blue-600/20 blur-xl rounded-full"></div>
            </div>
          </div>

          <p className="text-sm text-gray-300 mb-6 italic">The chain of identity starts with you.</p>

          <div className="mb-6">
            <p className="text-sm text-gray-400 mb-4">Earn your badge by verifying:</p>
            <div className="grid grid-cols-4 gap-3 max-w-md mx-auto">
              <div className="p-3 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-1">
                <Mail className="w-5 h-5" />
                <span className="text-xs">Email</span>
              </div>
              <div className="p-3 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-1">
                <Twitter className="w-5 h-5" />
                <span className="text-xs">X</span>
              </div>
              <div className="p-3 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-1">
                <MessageCircle className="w-5 h-5" />
                <span className="text-xs">Telegram</span>
              </div>
              <div className="p-3 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-1">
                <Users className="w-5 h-5" />
                <span className="text-xs">Discord</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setCurrentStep('email')}
            className="px-6 py-3 bg-white text-black rounded-xl font-semibold hover:bg-gray-200 transition-all transform hover:scale-105 inline-flex items-center gap-2"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </button>

          {/* Add login option for returning users */}
          <p className="mt-4 text-sm text-gray-400">
            Already have a badge? 
            <button
              onClick={() => {
                const savedEmail = localStorage.getItem('userEmail');
                if (savedEmail) {
                  setEmail(savedEmail);
                  setEmailInput(savedEmail);
                }
                setCurrentStep('email');
              }}
              className="ml-2 text-white hover:text-gray-300 underline transition-colors"
            >
              Login here
            </button>
          </p>
        </div>
      </div>
    );
  }

  // Email Input Page
  if (currentStep === 'email') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        {showProgress && (
          <ProgressIndicator 
            currentStep={currentStep} 
            totalSteps={totalTasks} 
            completedTasks={completedTasks}
          />
        )}
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10 mt-24">
          <button
            onClick={() => setCurrentStep('welcome')}
            className="mb-8 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
              <Mail className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Verify your email</h2>
            <p className="text-gray-400">We'll send you a verification code</p>
          </div>

          <div className="space-y-4">
            <input
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-white transition-colors"
              onKeyPress={(e) => e.key === 'Enter' && handleSendVerificationCode()}
            />
            
            <button
              onClick={handleSendVerificationCode}
              disabled={isLoading || !emailInput || !emailInput.includes('@')}
              className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Send Code
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
            
            {localStorage.getItem('userEmail') && (
              <button
                onClick={() => {
                  localStorage.removeItem('userEmail');
                  setEmailInput('');
                  setEmail('');
                }}
                className="w-full py-2 text-gray-400 hover:text-white transition-colors text-sm"
              >
                Use a different email
              </button>
            )}
          </div>

          <p className="text-xs text-gray-500 text-center mt-6">
            Your email is used only for badge verification and will not be shared.
          </p>
        </div>
      </div>
    );
  }

  // Email Verification Code Page
  if (currentStep === 'email-verify') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        {showProgress && (
          <ProgressIndicator 
            currentStep="email" 
            totalSteps={totalTasks} 
            completedTasks={completedTasks}
          />
        )}
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10 mt-24">
          <button
            onClick={() => setCurrentStep('email')}
            className="mb-8 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-green-500/10 rounded-xl flex items-center justify-center">
              <Mail className="w-8 h-8 text-green-400" />
            </div>
            <h2 className="text-3xl font-bold mb-4">
              {isReturningUser ? 'Welcome Back!' : 'Check your email'}
            </h2>
            <p className="text-gray-400">
              {isReturningUser 
                ? `We sent a verification code to ${email}` 
                : `We sent a code to ${email}`
              }
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength="6"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white text-center text-2xl tracking-widest placeholder-gray-500 focus:outline-none focus:border-white transition-colors"
              onKeyPress={(e) => e.key === 'Enter' && handleVerifyCode()}
            />
            
            <button
              onClick={handleVerifyCode}
              disabled={isLoading || verificationCode.length !== 6}
              className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Verify'
              )}
            </button>

            <button
              onClick={handleSendVerificationCode}
              disabled={resendTimer > 0}
              className="w-full py-2 text-gray-400 hover:text-white transition-colors disabled:cursor-not-allowed"
            >
              {resendTimer > 0 ? `Resend code in ${resendTimer}s` : 'Resend code'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Twitter Verification Page
  if (currentStep === 'twitter') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        {showProgress && (
          <ProgressIndicator 
            currentStep={currentStep} 
            totalSteps={totalTasks} 
            completedTasks={completedTasks}
          />
        )}
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10 mt-24">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
              <Twitter className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Connect X (Twitter)</h2>
            <p className="text-gray-400 mb-8">Follow @IOPn_io and connect your account</p>

            {twitterAttempted && (
              <div className="bg-orange-900/20 border border-orange-600/50 rounded-xl p-4 mb-6">
                <p className="text-orange-400 text-sm">
                  Make sure you're following @IOPn_io before connecting
                </p>
              </div>
            )}

            <div className="bg-white/5 rounded-xl p-6 mb-8 text-left">
              <h3 className="text-sm font-semibold mb-3 text-blue-400">Quick Steps:</h3>
              <ol className="space-y-2 text-sm text-gray-300">
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">1.</span>
                  <span>Click the button below to connect your X account</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">2.</span>
                  <span>Authorize the connection when prompted</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">3.</span>
                  <span>Make sure you're following @IOPn_io</span>
                </li>
              </ol>
            </div>

            <button
              onClick={handleTwitterAuth}
              disabled={isLoading}
              className="w-full py-4 px-6 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl font-semibold hover:from-blue-600 hover:to-blue-700 transition-all flex items-center justify-center space-x-3 group"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Twitter className="w-5 h-5" />
                  <span>Connect X Account</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>

            <div className="mt-6">
              <p className="text-xs text-gray-500 mb-3">Haven't followed yet?</p>
              <a
                href="https://twitter.com/IOPn_io"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-blue-400 hover:text-blue-300 transition-colors text-sm"
              >
                <span>Follow @IOPn_io</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Telegram Verification Page
  if (currentStep === 'telegram') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        {showProgress && (
          <ProgressIndicator 
            currentStep={currentStep} 
            totalSteps={totalTasks} 
            completedTasks={completedTasks}
          />
        )}
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10 mt-24">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
              <MessageCircle className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Join Telegram</h2>
            <p className="text-gray-400 mb-8">Join our Telegram channel to continue</p>

            <div className="bg-gray-900/50 rounded-xl p-6 mb-8 border border-gray-800">
              <h3 className="font-semibold mb-4">What happens next?</h3>
              <ul className="text-sm text-gray-400 space-y-2 text-left">
                <li>• Click the button to open our bot</li>
                <li>• Start the bot and follow instructions</li>
                <li>• We'll verify your membership automatically</li>
              </ul>
            </div>
           
            <button
              onClick={handleTelegramAuth}
              className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all flex items-center justify-center gap-2"
            >
              <MessageCircle className="w-5 h-5" />
              Open Telegram Bot
            </button>

            <button
              onClick={() => {
                checkStatus();
                setTimeout(() => {
                  if (tasks.telegram) {
                    showNotification('success', 'Telegram Verified!', 'Moving to Discord...');
                    setTimeout(() => setCurrentStep('discord'), 1500);
                  } else {
                    showNotification('info', 'Still Waiting', 'Complete verification in Telegram first');
                  }
                }, 500);
              }}
              className="w-full py-3 bg-gray-800 text-white rounded-xl font-medium hover:bg-gray-700 transition-all mt-3 flex items-center justify-center gap-2"
            >
              <ArrowRight className="w-5 h-5 rotate-180" />
              Check Status
            </button>

            <button
              onClick={() => setCurrentStep('discord')}
              className="mt-4 text-gray-400 hover:text-white transition-colors"
            >
              Skip for now →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Discord Verification Page
  if (currentStep === 'discord') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        {showProgress && (
          <ProgressIndicator 
            currentStep={currentStep} 
            totalSteps={totalTasks} 
            completedTasks={completedTasks}
          />
        )}
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10 mt-24">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
              <Users className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Join Discord</h2>
            <p className="text-gray-400 mb-8">Join our Discord server to continue</p>

            {discordAttempted && !tasks.discord && (
              <div className="bg-red-900/20 border border-red-600/50 rounded-xl p-4 mb-6">
                <p className="text-red-400 text-sm font-semibold mb-2">
                  You're not in the IOPn Discord server!
                </p>
                <p className="text-red-300 text-xs mb-3">
                  Please join our Discord server first, then try connecting again.
                </p>
                {discordInviteLink && (
                  <a
                    href={`https://${discordInviteLink}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 px-3 py-2 rounded-lg text-sm transition-colors"
                  >
                    <Users className="w-4 h-4" />
                    <span>Join Discord Server</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            )}

            <div className="bg-white/5 rounded-xl p-6 mb-8 text-left">
              <h3 className="text-sm font-semibold mb-3 text-purple-400">Quick Steps:</h3>
              <ol className="space-y-2 text-sm text-gray-300">
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">1.</span>
                  <span>Join the IOPn Discord server first</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">2.</span>
                  <span>Click "Connect Discord" below</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">3.</span>
                  <span>Authorize the connection when prompted</span>
                </li>
              </ol>
            </div>

            <button
              onClick={handleDiscordAuth}
              disabled={isLoading}
              className="w-full py-4 px-6 bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl font-semibold hover:from-purple-600 hover:to-purple-700 transition-all flex items-center justify-center space-x-3 group disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Users className="w-5 h-5" />
                  <span>{discordAttempted ? 'Try Connecting Again' : 'Connect Discord'}</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>

            <div className="mt-6">
              <p className="text-xs text-gray-500 mb-3">Not in the server yet?</p>
              <a
                href="https://discord.gg/iopn"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-purple-400 hover:text-purple-300 transition-colors text-sm"
              >
                <span>Join IOPn Discord</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>

            <button
              onClick={() => setCurrentStep('summary')}
              className="mt-4 text-gray-400 hover:text-white transition-colors"
            >
              Skip for now →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Summary Page
  if (currentStep === 'summary') {
    const canClaim = completedTasks === totalTasks;
    
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/50" />
        </div>

        <div className="w-full max-w-2xl relative z-10">
          <div className="text-center mb-8">
            <img src={`${process.env.PUBLIC_URL}/logo.png`} alt="IOPn Logo" className="w-16 h-16 mb-6 mx-auto" />
            <h1 className="text-4xl font-bold mb-2">Your Progress</h1>
            <p className="text-gray-400">{canClaim ? 'All tasks completed! Claim your badge.' : 'Complete all tasks to claim your badge.'}</p>
          </div>

          <div className="mb-8">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-400">Progress</span>
              <span className="text-sm text-gray-400">{completedTasks}/{totalTasks} completed</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
                style={{ width: `${(completedTasks / totalTasks) * 100}%` }}
              />
            </div>
          </div>

          <div className="space-y-4 mb-8">
            <div className={`p-4 rounded-2xl border ${tasks.email ? 'border-green-500/50 bg-green-500/10' : 'border-gray-800 bg-gray-900/50'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5" />
                  <span>Email verified</span>
                </div>
                {tasks.email ? <Check className="w-5 h-5 text-green-400" /> : 
                  <button onClick={() => setCurrentStep('email')} className="text-sm text-blue-400 hover:underline">Verify</button>
                }
              </div>
            </div>

            <div className={`p-4 rounded-2xl border ${tasks.twitter ? 'border-green-500/50 bg-green-500/10' : 'border-gray-800 bg-gray-900/50'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Twitter className="w-5 h-5" />
                  <span>Following @IOPn_io on X</span>
                </div>
                {tasks.twitter ? <Check className="w-5 h-5 text-green-400" /> : 
                  <button onClick={() => setCurrentStep('twitter')} className="text-sm text-blue-400 hover:underline">Connect</button>
                }
              </div>
            </div>

            <div className={`p-4 rounded-2xl border ${tasks.telegram ? 'border-green-500/50 bg-green-500/10' : 'border-gray-800 bg-gray-900/50'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MessageCircle className="w-5 h-5" />
                  <span>Joined IOPn Telegram</span>
                </div>
                {tasks.telegram ? <Check className="w-5 h-5 text-green-400" /> : 
                  <button onClick={() => setCurrentStep('telegram')} className="text-sm text-blue-400 hover:underline">Join</button>
                }
              </div>
            </div>

            <div className={`p-4 rounded-2xl border ${tasks.discord ? 'border-green-500/50 bg-green-500/10' : 'border-gray-800 bg-gray-900/50'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Users className="w-5 h-5" />
                  <span>Joined IOPn Discord</span>
                </div>
                {tasks.discord ? <Check className="w-5 h-5 text-green-400" /> : 
                  <button onClick={() => setCurrentStep('discord')} className="text-sm text-blue-400 hover:underline">Join</button>
                }
              </div>
            </div>
          </div>

          <button
            onClick={handleClaim}
            disabled={!canClaim || isLoading}
            className={`w-full py-4 rounded-2xl font-medium text-lg transition-all ${
              canClaim 
                ? 'bg-white text-black hover:bg-gray-200 transform hover:scale-[1.02]' 
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : 'Claim Your Badge'}
          </button>
        </div>
      </div>
    );
  }

  // Claimed Page
  if (currentStep === 'claimed') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <Notification 
          {...notification} 
          onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
        />
        
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/70" />
        </div>

        <div className="w-full max-w-2xl relative z-10 text-center">
          <h1 className="text-3xl md:text-4xl font-bold mb-6">Congratulations</h1>

          <div className="mb-6">
            <img 
              src={`${process.env.PUBLIC_URL}/badgef.png`} 
              alt="IOPn Early Badge" 
              className="w-80 h-80 md:w-96 md:h-96 lg:w-[28rem] lg:h-[28rem] mx-auto rounded-2xl shadow-2xl object-contain opacity-90" 
            />
          </div>

          <p className="text-lg text-gray-300 mb-6">You've earned your Early n-Badge!</p>

          <div className="max-w-md mx-auto space-y-3">
            <button 
              onClick={() => setCurrentStep('dashboard')} 
              className="w-full py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-medium hover:from-purple-700 hover:to-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              <TrendingUp className="w-5 h-5" />
              View Dashboard
            </button>
            
            <button 
              onClick={shareOnTwitter} 
              className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
            >
              <Share2 className="w-5 h-5" />
              Share on X
            </button>
            
            <button 
              onClick={() => copyToClipboard(referralLink, 'referral')} 
              className="w-full py-3 bg-white/10 text-white border border-white/20 rounded-xl font-medium hover:bg-white/20 transition-colors flex items-center justify-center gap-2"
            >
              <Copy className="w-5 h-5" />
              {copiedText === 'referral' ? 'Copied!' : 'Copy Referral Link'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 'dashboard') {
    return <UserDashboard 
      email={email} 
      onLogout={() => {
        localStorage.removeItem('userEmail');
        localStorage.removeItem('referralCode');
        setEmail('');
        setCurrentStep('welcome');
        setTasks({
          email: false,
          twitter: false,
          telegram: false,
          discord: false
        });
      }} 
    />;
  }

  return null;
};

export default SocialDashboard;