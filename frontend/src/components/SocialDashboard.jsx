import React, { useState, useEffect } from 'react';
import { Check,Trophy, Twitter, MessageCircle,Clock, AlertCircle, Users, Link2, Mail, Loader2, ArrowRight, Copy, Download, Share2, ExternalLink, ArrowLeft, X, CheckCircle, Info, TrendingUp } from 'lucide-react';
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
  const [isLoginFlow, setIsLoginFlow] = useState(false);
  const [rewardInfo, setRewardInfo] = useState(null);
    const [dashboardData, setDashboardData] = useState(null);
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

  const API_URL = process.env.REACT_APP_API_URL || 'https://badge.iopn.io';
  const TELEGRAM_BOT_USERNAME = process.env.REACT_APP_TELEGRAM_BOT_USERNAME || 'iopn_badge_bot';

  const completedTasks = Object.values(tasks).filter(Boolean).length;
  const totalTasks = 4;


  const copyBadgeImage = async () => {
  try {
    // Fetch the badge image
    const response = await fetch(`${process.env.PUBLIC_URL}/badgef.png`);
    const blob = await response.blob();
    
    // Check if the Clipboard API supports writing images
    if (navigator.clipboard && window.ClipboardItem) {
      const item = new ClipboardItem({ 'image/png': blob });
      await navigator.clipboard.write([item]);
      
      showNotification('success', 'Badge Copied!', 'You can now paste your badge image on Twitter');
      setCopiedText('badge');
      setTimeout(() => setCopiedText(''), 2000);
    } else {
      // Fallback for browsers that don't support clipboard image
      showNotification('info', 'Not Supported', 'Your browser doesn\'t support copying images. Right-click the badge and select "Copy Image"');
    }
  } catch (error) {
    console.error('Error copying badge:', error);
    showNotification('error', 'Copy Failed', 'Please right-click the badge and select "Copy Image"');
  }
};



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
  console.log('checkStatus called with email:', userEmail);
  
  if (!userEmail) {
    console.log('No email available for status check');
    return null;
  }

  try {
    const response = await fetch(`${API_URL}/api/status/${encodeURIComponent(userEmail)}`);
    
    if (!response.ok) {
      if (response.status === 404) {
        console.log('User not found - new user');
        return null;
      }
      if (response.status >= 500) {
        console.error('Server error:', response.status);
        return null;
      }
      throw new Error(`Status check failed: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Status response:', data);
      
    if (data && data.exists && data.tasks) {
      setTasks(data.tasks);
      setEmail(userEmail);
      
      // Only fetch dashboard data if badge is issued AND we're going to dashboard
      if (data.badge_issued) {
        // Don't fetch dashboard here - let the dashboard page handle it
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
 // Check OAuth callbacks
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const platform = urlParams.get('platform');
  const status = urlParams.get('status');
  const message = urlParams.get('message');
  const username = urlParams.get('username');
  const invite = urlParams.get('invite');
  const refFromUrl = urlParams.get('ref');
  const savedEmail = localStorage.getItem('userEmail');

  // Always preserve referral code
  if (refFromUrl) {
    setReferralCode(refFromUrl);
    localStorage.setItem('referralCode', refFromUrl);
  }

  if (platform && status) {
    // Make sure we have an email
    if (!savedEmail) {
      console.error('No email found after OAuth callback');
      setCurrentStep('email');
      showNotification('error', 'Session Lost', 'Please verify your email again');
      return;
    }

    // Set the email in state
    setEmail(savedEmail);
    
    if (status === 'success') {
      // Update tasks immediately
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
      
      // Check complete status before navigating
      setTimeout(async () => {
        const statusData = await checkStatus(savedEmail);
        
        if (statusData) {
          // Let checkStatus handle navigation
          console.log('Status checked, navigation handled by checkStatus');
        } else {
          // Fallback navigation
          if (platform === 'twitter') {
            setCurrentStep('telegram');
          } else if (platform === 'discord') {
            setCurrentStep('summary');
          }
        }
      }, 1000);
      
    } else if (status === 'duplicate') {
      // Handle duplicate account error
      const decodedMessage = message ? decodeURIComponent(message) : 'This account is already linked';
      showNotification('error', 'Account Already Used', decodedMessage);
      
      // Navigate back to the task
      if (platform === 'twitter') {
        setCurrentStep('twitter');
      } else if (platform === 'discord') {
        setCurrentStep('discord');
      }
    } else if (status === 'not_in_server' && platform === 'discord') {
      // FIXED: Handle Discord not in server status (was checking for 'not_member')
      setDiscordAttempted(true);
      setDiscordInviteLink(invite || 'discord.gg/iopn');
      
      showNotification(
        'warning', 
        'Join Our Discord First!', 
        'You authenticated successfully, but you need to join the IOPn Discord server to complete this task.'
      );
      
      setCurrentStep('discord');
    } else if (status === 'error') {
      // Handle general errors
      const errorMessage = message ? decodeURIComponent(message) : 'An error occurred. Please try again.';
      
      showNotification('error', 'Error', errorMessage);
      
      // Navigate back to the appropriate step
      if (platform === 'twitter') {
        setCurrentStep('twitter');
      } else if (platform === 'discord') {
        setCurrentStep('discord');
      }
    }
    
    // Clear URL params but preserve referral code
    const newUrl = refFromUrl ? `${window.location.pathname}?ref=${refFromUrl}` : window.location.pathname;
    window.history.replaceState({}, document.title, newUrl);
  }
}, []);

  // Check status on mount
// Check status on mount
useEffect(() => {
  const savedEmail = localStorage.getItem('userEmail');
  const urlParams = new URLSearchParams(window.location.search);
  const platform = urlParams.get('platform');
  const refFromUrl = urlParams.get('ref');
  
  // Save referral code if present
  if (refFromUrl) {
    setReferralCode(refFromUrl);
    localStorage.setItem('referralCode', refFromUrl);
  }
  
  // Only check status if we have email and not handling OAuth
  if (savedEmail && !platform) {
    setEmail(savedEmail);
    // Add small delay to prevent race conditions
    setTimeout(() => {
      checkStatus(savedEmail);
    }, 100);
  } else if (!savedEmail && !platform) {
    setCurrentStep('welcome');
  }
  // Don't make any API calls on initial mount
}, []); // Empty dependency array - only run once
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

 useEffect(() => {
  // Only fetch when we have email AND we're on the dashboard page
  if (email ) {
    fetchDashboardData();
    // Longer interval to reduce server load
    const interval = setInterval(fetchDashboardData, 60000); // 60 seconds
    return () => clearInterval(interval);
  }
}, [email, currentStep]);

   const fetchDashboardData = async () => {
  // Don't fetch if no email or not on dashboard page
  if (!email || currentStep !== 'dashboard') {
    console.log('Skipping dashboard fetch - no email or not on dashboard page');
    return;
  }
  
  try {
    // MUST include the email parameter
    const response = await fetch(`${API_URL}/api/dashboard/${encodeURIComponent(email)}`);
    
    if (!response.ok) {
      if (response.status === 404) {
        console.log('User not found in dashboard');
        return;
      }
      throw new Error(`Dashboard fetch failed: ${response.status}`);
    }
    
    const data = await response.json();
    setDashboardData(data);
  } catch (error) {
    console.error('Error fetching dashboard:', error);
  } finally {
    setIsLoading(false);
  }
};

 const handleSendVerificationCode = async () => {
  if (!emailInput || !emailInput.includes('@')) {
    showNotification('error', 'Invalid Email', 'Please enter a valid email address');
    return;
  }

  setIsLoading(true);
  try {
    // First, check if user exists
    const checkResponse = await fetch(`${API_URL}/api/status/${encodeURIComponent(emailInput)}`);
    const checkData = await checkResponse.json();
    
    if (checkData.exists) {
      // EXISTING USER - Always require verification code
      setIsReturningUser(true);
      
      // Send verification code
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
    } else {
      // NEW USER
      if (isLoginFlow) {
        // They clicked "login" but account doesn't exist
        showNotification('error', 'Account Not Found', 'No account found with this email. Please sign up first.');
        setIsLoginFlow(false); // Switch back to signup mode
      } else {
        // NEW SIGNUP - Skip verification!
        const response = await fetch(`${API_URL}/auth/email/register-instant`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            email: emailInput,
            referral_code: referralCode || localStorage.getItem('referralCode') || ''
          })
        });

        if (response.ok) {
          const data = await response.json();
          
          // Save email and mark as verified
          setEmail(emailInput);
          localStorage.setItem('userEmail', emailInput);
          setTasks(prev => ({ ...prev, email: true }));
          
          // Save the user's referral code if returned
          if (data.referral_code) {
            setUserReferralCode(data.referral_code);
          }
          
          showNotification('success', 'Welcome to IOPn!', 'Account created successfully');
          
          // Move directly to Twitter step
          setTimeout(() => setCurrentStep('twitter'), 1500);
        } else {
          const error = await response.json();
          showNotification('error', 'Signup Failed', error.detail || 'Please try again');
        }
      }
    }
  } catch (error) {
    console.error('Email process error:', error);
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


    const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    setTimeout(() => setCopiedText(''), 2000);
  };

    const getReferralLink = () => {
    return `https://badge.iopn.io/?ref=${dashboardData?.user?.referral_code || ''}`;
  };



const handleTwitterAuth = async () => {
  setIsLoading(true);
  try {
    // Get referral code from all possible sources
    const refCode = referralCode || localStorage.getItem('referralCode') || new URLSearchParams(window.location.search).get('ref') || '';
    
    // Include referral code in the request
    const response = await fetch(`${API_URL}/auth/twitter/login?email=${encodeURIComponent(email)}&ref=${encodeURIComponent(refCode)}`);
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
  const refCode = referralCode || localStorage.getItem('referralCode') || new URLSearchParams(window.location.search).get('ref') || '';
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
    const refCode = referralCode || localStorage.getItem('referralCode') || new URLSearchParams(window.location.search).get('ref') || '';
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
    const refCode = referralCode || localStorage.getItem('referralCode') || '';
    
    const response = await fetch(`${API_URL}/api/claim-badge-with-referral`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email: email,
        referral_code: refCode
      })
    });

    const data = await response.json();
    
    if (response.ok && data.success) {
      // Removed the referral notification that was causing the error
      
      // Fetch user's referral code for the celebration page
      try {
        const dashResponse = await fetch(`${API_URL}/api/dashboard/${encodeURIComponent(email)}`);
        if (dashResponse.ok) {
          const dashData = await dashResponse.json();
          setUserReferralCode(dashData.user.referral_code);
          // Don't set dashboard data here - let dashboard page fetch it
        }
      } catch (err) {
        console.error('Error fetching referral code:', err);
      }
      
      // Show celebration screen instead of dashboard
      setTimeout(() => {
        setCurrentStep('celebration');
      }, 1000);
    } else {
      showNotification('error', 'Claim Failed', data.detail || data.error || 'Please try again');
    }
  } catch (error) {
    console.error('Claim error:', error);
    showNotification('error', 'Network Error', 'Failed to claim badge. Please try again.');
  } finally {
    setIsLoading(false);
  }
};

const shareOnTwitter = () => {
  const referralLink = userReferralCode ? `https://badge.iopn.io/?ref=${userReferralCode}` : 'https://badge.iopn.io';
  const text = `I just claimed my Early n-Badge from @IOPn_io! 🚀\n\nJoin the identity revolution:\n${referralLink}\n`;
  
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

          <h1 className="text-3xl md:text-4xl font-bold mb-3">Welcome back to IOPn</h1>
          <p className="text-lg text-gray-300 mb-4">Access your sovereign identity</p>

          <p className="text-sm text-gray-400 mb-6 max-w-lg mx-auto">
            The Early n-Badge claim has ended. Badge holders can login to access their dashboard and manage their identity.
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

          <p className="text-sm text-gray-300 mb-6 italic">The chain of identity continues with you.</p>

          <button
            onClick={() => {
              setIsLoginFlow(true); // Ensure login flow is set
              setCurrentStep('email');
            }}
            className="px-6 py-3 bg-white text-black rounded-xl font-semibold hover:bg-gray-200 transition-all transform hover:scale-105 inline-flex items-center gap-2"
          >
            Login to Dashboard
            <ArrowRight className="w-4 h-4" />
          </button>

          <p className="mt-6 text-sm text-gray-400">
            Don't have a badge yet? The claim period has ended.
          </p>
          
          <p className="mt-2 text-xs text-gray-500">
            Stay tuned for future opportunities on our testnet.
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
          onClick={() => {
            setCurrentStep('welcome');
            setIsLoginFlow(false);
          }}
          className="mb-8 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
            <Mail className="w-8 h-8" />
          </div>
          <h2 className="text-3xl font-bold mb-4">
            {isLoginFlow ? 'Welcome Back!' : 'Get Started'}
          </h2>
          <p className="text-gray-400">
            {isLoginFlow 
              ? "Enter your email to receive a login code" 
              : "Enter your email to create your account instantly"
            }
          </p>
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
                {isLoginFlow ? 'Send Login Code' : 'Create Account'}
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
          
          {/* Toggle between signup and login */}
          <div className="text-center pt-4 border-t border-gray-800">
            <button
              onClick={() => {
                setIsLoginFlow(!isLoginFlow);
                setEmailInput(''); // Clear email when switching
              }}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              {isLoginFlow 
                ? "Don't have an account? Sign up instead" 
                : "Already have an account? Login here"
              }
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-500 text-center mt-6">
          {isLoginFlow 
            ? "We'll send a verification code to your email" 
            : "No verification needed - start earning your badge immediately!"
          }
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
 // Discord Verification Page - Complete and Fixed
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
            <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div className="text-left">
                  <p className="text-yellow-400 text-sm font-semibold mb-1">
                    Join the Server First!
                  </p>
                  <p className="text-yellow-300 text-xs mb-3">
                    You authenticated with Discord, but you're not in our server yet. Join the IOPn Discord server, then try connecting again.
                  </p>
                  {discordInviteLink && (
                    <a
                      href={discordInviteLink.startsWith('http') ? discordInviteLink : `https://${discordInviteLink}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 px-3 py-2 rounded-lg text-sm transition-colors"
                    >
                      <Users className="w-4 h-4" />
                      <span>Join Discord Server</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
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


  // Badge Celebration Page
  if (currentStep === 'celebration') {
    return (
      <>
        <div className="h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
          <Notification 
            {...notification} 
            onClose={() => setNotification(prev => ({ ...prev, isVisible: false }))}
          />
          
          {/* Animated background */}
          <div className="absolute inset-0 w-full h-full">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-black to-blue-900/20" />
            <div className="absolute top-0 left-0 w-96 h-96 bg-purple-500 rounded-full filter blur-[128px] opacity-20 animate-pulse" />
            <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-500 rounded-full filter blur-[128px] opacity-20 animate-pulse" />
          </div>

          {/* Confetti container with fixed positioning */}
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="absolute animate-fall"
                style={{
                  left: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 3}s`,
                  animationDuration: `${3 + Math.random() * 2}s`
                }}
              >
                <div className={`w-3 h-3 ${i % 3 === 0 ? 'bg-purple-400' : i % 3 === 1 ? 'bg-blue-400' : 'bg-green-400'} rounded-full`} />
              </div>
            ))}
          </div>

          <div className="w-full max-w-2xl relative z-10 text-center">
            <div className="mb-6 animate-bounce-slow">
              <Trophy className="w-20 h-20 mx-auto text-yellow-400 mb-2" />
            </div>

            <h1 className="text-3xl md:text-4xl font-bold mb-3 animate-fade-in">
              Congratulations! 🎉
            </h1>
            
            <p className="text-lg text-gray-300 mb-6 animate-fade-in-delay">
              You've earned your IOPn Early n-Badge
            </p>

            <div className="mb-6 animate-scale-in relative">
              <div className="relative inline-block">
                <img 
                  src={`${process.env.PUBLIC_URL}/badgef.png`} 
                  alt="IOPn Early Badge" 
                  className="w-48 h-48 md:w-64 md:h-64 rounded-2xl shadow-2xl ring-4 ring-white/20" 
                />
                
                {/* Copy Badge Button - positioned below the image */}
                <button
                  onClick={copyBadgeImage}
                  className="mt-4 px-4 py-2 bg-black/80 backdrop-blur-sm text-white rounded-lg border border-white/20 hover:bg-black/90 transition-all flex items-center gap-2 mx-auto"
                >
                  {copiedText === 'badge' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      <span className="text-green-400 text-sm">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span className="text-sm">Copy Badge</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-3 animate-fade-in-delay-2">
              <button 
                onClick={shareOnTwitter} 
                className="w-full max-w-sm mx-auto py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all flex items-center justify-center gap-2 group transform hover:scale-105"
              >
                <Twitter className="w-5 h-5" />
                Share on X
                <Share2 className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              
              <button 
                onClick={() => copyToClipboard(getReferralLink(), 'referral')} 
                className="w-full max-w-sm mx-auto py-3 bg-white/10 text-white border border-white/20 rounded-xl font-medium hover:bg-white/20 transition-all flex items-center justify-center gap-2 transform hover:scale-105"
              >
                <Copy className="w-5 h-5" />
                {copiedText === 'referral' ? 'Copied!' : 'Copy Referral Link'}
              </button>
              
              <button 
                onClick={() => setCurrentStep('dashboard')} 
                className="w-full max-w-sm mx-auto py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-medium hover:from-purple-700 hover:to-blue-700 transition-all flex items-center justify-center gap-2 transform hover:scale-105"
              >
                <TrendingUp className="w-5 h-5" />
                View Dashboard
              </button>
            </div>

            <p className="text-sm text-gray-500 mt-6">
              Your unique referral code: <span className="text-white font-mono">{userReferralCode}</span>
            </p>
          </div>
        </div>
      </>
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
    dashboardData={dashboardData} // Pass the data if you have it
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
      setDashboardData(null); // Clear dashboard data on logout
    }} 
  />;
  }

  return null;
};

export default SocialDashboard;