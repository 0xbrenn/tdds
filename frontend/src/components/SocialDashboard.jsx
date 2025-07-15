import React, { useState, useEffect } from 'react';
import { Check, Twitter, MessageCircle, Users, Link2, Mail, Loader2, ArrowRight, Copy, Download, Share2, ExternalLink, ArrowLeft } from 'lucide-react';

const SocialDashboard = () => {
  const [currentStep, setCurrentStep] = useState('welcome'); 
  // Steps: 'welcome', 'email', 'email-verify', 'twitter', 'telegram', 'discord', 'summary', 'claimed'
  
  const [email, setEmail] = useState('');
  const [emailInput, setEmailInput] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [tasks, setTasks] = useState({
    email: false,
    twitter: false,
    telegram: false,
    discord: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [referralLink] = useState(`https://iopn.io/ref/${Math.random().toString(36).substr(2, 8).toUpperCase()}`);
  const [copiedText, setCopiedText] = useState('');
  const [showBadgeAnimation, setShowBadgeAnimation] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);
  const [twitterAttempted, setTwitterAttempted] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  const TELEGRAM_BOT_USERNAME = process.env.REACT_APP_TELEGRAM_BOT_USERNAME || 'iopn_badge_bot';

  const completedTasks = Object.values(tasks).filter(Boolean).length;
  const totalTasks = 4;

  // Timer for resend code
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Check status function
  const checkStatus = async () => {
    const userEmail = email || localStorage.getItem('userEmail');
    if (!userEmail) return;

    try {
      const response = await fetch(`${API_URL}/api/status/${encodeURIComponent(userEmail)}`);
      const data = await response.json();
      
      if (data.exists && data.tasks) {
        setTasks(data.tasks);
        
        // Determine which step to show based on completed tasks
        if (!data.tasks.email) {
          setCurrentStep('email');
        } else if (!data.tasks.twitter) {
          setCurrentStep('twitter');
        } else if (!data.tasks.telegram) {
          setCurrentStep('telegram');
        } else if (!data.tasks.discord) {
          setCurrentStep('discord');
        } else if (data.badge_issued) {
          setCurrentStep('claimed');
        } else {
          setCurrentStep('summary');
        }
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  // Check OAuth callbacks and initial status
 // In your useEffect for OAuth callbacks
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const platform = urlParams.get('platform');
  const status = urlParams.get('status');
  const username = urlParams.get('username');
  
  // Restore email from localStorage if coming back from OAuth
  const savedEmail = localStorage.getItem('userEmail');
  if (savedEmail && !email) {
    setEmail(savedEmail);
    setTasks(prev => ({ ...prev, email: true }));
  }
  
  if (platform && status) {
    if (status === 'success') {
      setTasks(prev => ({ ...prev, [platform]: true }));
      // Check status after OAuth success to determine next step
      setTimeout(() => checkStatus(), 100);
    } else if (status === 'not_following' || status === 'not_member') {
      // Set attempted flag for better UX
      if (platform === 'twitter') {
        setTwitterAttempted(true);
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
      checkStatus();
    }
  }, []);

  // Badge animation
  useEffect(() => {
    if (currentStep === 'welcome') {
      setTimeout(() => setShowBadgeAnimation(true), 100);
    }
  }, [currentStep]);

  const handleSendVerificationCode = async () => {
    if (!emailInput || !emailInput.includes('@')) {
      alert('Please enter a valid email address');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/email/send-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailInput })
      });

      if (response.ok) {
        setEmail(emailInput);
        setCurrentStep('email-verify');
        setResendTimer(60); // 60 second cooldown
      } else {
        alert('Failed to send verification code. Please try again.');
      }
    } catch (error) {
      console.error('Send verification error:', error);
      alert('Failed to send verification code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      alert('Please enter the 6-digit code');
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
        setTasks(prev => ({ ...prev, email: true }));
        localStorage.setItem('userEmail', email);
        setCurrentStep('twitter');
      } else {
        const error = await response.json();
        alert(error.detail || 'Invalid code. Please try again.');
      }
    } catch (error) {
      console.error('Verify code error:', error);
      alert('Failed to verify code. Please try again.');
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
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Twitter auth error:', error);
      alert('Failed to connect Twitter. Please try again.');
      setIsLoading(false);
    }
  };

  const handleTelegramAuth = () => {
   const encodedEmail = btoa(email); // Base64 encode the email
  const botUrl = `https://t.me/${TELEGRAM_BOT_USERNAME}?start=verify_${encodedEmail}`;
  console.log('Opening bot with URL:', botUrl);
  window.open(botUrl, '_blank');
    
    // Poll for verification
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const response = await fetch(`${API_URL}/api/status/${encodeURIComponent(email)}`);
        const data = await response.json();
        
        if (data.tasks && data.tasks.telegram) {
          setTasks(prev => ({ ...prev, telegram: true }));
          clearInterval(interval);
          setCurrentStep('discord');
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
      
      if (attempts >= 20) clearInterval(interval);
    }, 3000);
  };

  const handleDiscordAuth = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/discord/login?email=${encodeURIComponent(email)}`);
      const data = await response.json();
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Discord auth error:', error);
      alert('Failed to connect Discord. Please try again.');
      setIsLoading(false);
    }
  };

  const handleClaim = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/badge/claim`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const data = await response.json();
      if (data.success) {
        setCurrentStep('claimed');
      } else {
        alert(data.error || 'Failed to claim badge. Please try again.');
      }
    } catch (error) {
      console.error('Claim error:', error);
      alert('Failed to claim badge. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    setTimeout(() => setCopiedText(''), 2000);
  };

  const shareOnTwitter = () => {
    const text = `I just claimed my Early n-Badge from @IOPn_io! 🚀\n\nJoin the identity revolution:\n${referralLink}`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
  };

  // Welcome Page
  if (currentStep === 'welcome') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="relative z-10 max-w-2xl w-full text-center">
          <img src={`${process.env.PUBLIC_URL}/logo.png`} alt="IOPn Logo" className="w-24 h-24 mb-8 mx-auto" />
          
          <h1 className="text-5xl font-bold mb-6">Welcome to the sovereign stack.</h1>
          <p className="text-xl text-gray-300 mb-8">This is your first step toward the identity layer.</p>
          
          <p className="text-lg text-gray-400 mb-12 max-w-lg mx-auto">
            The Early n-Badge marks you as one of the first. One of the sovereign.
            Claiming it now will give you an edge during the upcoming Testnet - including access,
            multipliers, and REP advantages.
          </p>

          <div className={`mb-8 transition-all duration-1200 ease-out ${
            showBadgeAnimation ? 'opacity-100 transform scale-100' : 'opacity-0 transform scale-90'
          }`}>
            <div className="w-32 h-32 mx-auto bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center animate-pulse">
              <span className="text-5xl font-bold">n</span>
            </div>
          </div>

          <p className="text-lg text-gray-300 mb-12 italic">The chain of identity starts with you.</p>

          <div className="mb-8">
            <p className="text-lg text-gray-400 mb-6">Earn your badge by verifying:</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-xl mx-auto mb-8">
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-2">
                <Mail className="w-6 h-6" />
                <span className="text-sm">Email</span>
              </div>
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-2">
                <Twitter className="w-6 h-6" />
                <span className="text-sm">X (Twitter)</span>
              </div>
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-2">
                <MessageCircle className="w-6 h-6" />
                <span className="text-sm">Telegram</span>
              </div>
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center gap-2">
                <Users className="w-6 h-6" />
                <span className="text-sm">Discord</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setCurrentStep('email')}
            className="px-8 py-4 bg-white text-black rounded-xl font-semibold text-lg hover:bg-gray-200 transition-all transform hover:scale-105 inline-flex items-center gap-3"
          >
            Get Started
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  // Email Input Page
  if (currentStep === 'email') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10">
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
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10">
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
            <h2 className="text-3xl font-bold mb-4">Check your email</h2>
            <p className="text-gray-400">We sent a code to {email}</p>
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

 // Update the Twitter Verification Page
if (currentStep === 'twitter') {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 w-full h-full bg-black">
        <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
          <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-black/60" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
            <Twitter className="w-8 h-8" />
          </div>
          <h2 className="text-3xl font-bold mb-4">Connect X (Twitter)</h2>
          <p className="text-gray-400 mb-8">Follow @IOPn_io to continue</p>

          {/* Show this message if they've tried but aren't following */}
          {twitterAttempted && !tasks.twitter && (
            <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-xl p-4 mb-6">
              <p className="text-yellow-400 text-sm font-semibold mb-2">
                You're not following @IOPn_io yet!
              </p>
              <p className="text-yellow-300 text-xs mb-3">
                Please follow our account first, then try connecting again.
              </p>
              <a 
                href="https://twitter.com/IOPn_io" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Twitter className="w-4 h-4" />
                Follow @IOPn_io
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          <div className="bg-gray-900/50 rounded-xl p-6 mb-8 border border-gray-800">
            <h3 className="font-semibold mb-4">Why connect X?</h3>
            <ul className="text-sm text-gray-400 space-y-2 text-left">
              <li>• Verify you're following @IOPn_io</li>
              <li>• Stay updated with IOPn announcements</li>
              <li>• Join the community conversation</li>
            </ul>
          </div>

          <button
            onClick={() => {
              setTwitterAttempted(true);
              handleTwitterAuth();
            }}
            disabled={isLoading}
            className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Twitter className="w-5 h-5" />
                {twitterAttempted ? 'Try Connecting Again' : 'Connect with X'}
              </>
            )}
          </button>

          <button
            onClick={() => setCurrentStep('telegram')}
            className="mt-4 text-gray-400 hover:text-white transition-colors"
          >
            Skip for now →
          </button>
        </div>
      </div>
    </div>
  );
}

  // Telegram Verification Page
  if (currentStep === 'telegram') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10">
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
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="w-full max-w-md relative z-10">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-white/10 rounded-xl flex items-center justify-center">
              <Users className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Join Discord</h2>
            <p className="text-gray-400 mb-8">Join our Discord server to continue</p>

            <div className="bg-gray-900/50 rounded-xl p-6 mb-8 border border-gray-800">
              <h3 className="font-semibold mb-4">Why join Discord?</h3>
              <ul className="text-sm text-gray-400 space-y-2 text-left">
                <li>• Connect with the IOPn community</li>
                <li>• Get early access to updates</li>
                <li>• Participate in exclusive events</li>
              </ul>
            </div>

            <button
              onClick={handleDiscordAuth}
              disabled={isLoading}
              className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Users className="w-5 h-5" />
                  Connect Discord
                </>
              )}
            </button>

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

  // Summary Page (replaces old tasks page)
  if (currentStep === 'summary') {
    const canClaim = completedTasks === totalTasks;
    
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
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

          {/* Progress Bar */}
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

          {/* Task Summary */}
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

  // Claimed Page (same as before)
  if (currentStep === 'claimed') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute inset-0 w-full h-full bg-black">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
            <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-black/70" />
        </div>

        <div className="w-full max-w-2xl relative z-10 text-center">
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-white/20 rounded-full mb-4 animate-pulse">
              <Check className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-5xl font-bold mb-4">Congratulations!</h1>
            <p className="text-2xl text-gray-300">You've successfully claimed your Early n-Badge!</p>
          </div>

          <div className="mb-12">
            <img src={`${process.env.PUBLIC_URL}/iopn-badge.png`} alt="IOPn Early Badge" className="w-64 h-64 mx-auto rounded-2xl shadow-2xl" />
          </div>

          <div className="max-w-md mx-auto space-y-4">
            <button onClick={shareOnTwitter} className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-gray-200 transition-colors flex items-center justify-center gap-2">
              <Share2 className="w-5 h-5" />
              Share on X
            </button>
            <button onClick={() => copyToClipboard(referralLink, 'referral')} className="w-full py-3 bg-white/10 text-white border border-white/20 rounded-xl font-medium hover:bg-white/20 transition-colors flex items-center justify-center gap-2">
              <Copy className="w-5 h-5" />
              {copiedText === 'referral' ? 'Copied!' : 'Copy Referral Link'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default SocialDashboard;