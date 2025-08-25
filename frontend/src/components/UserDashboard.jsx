// frontend/src/components/UserDashboard.jsx
import React, { useState, useEffect } from 'react';
import { Copy, Users, Gift, Loader2, ExternalLink, CheckCircle, Trophy, Sparkles, Star, TrendingUp, Share2, Twitter, LogOut, Zap, Clock, Award, BarChart3, AlertCircle, Dices, ArrowUp, Coins } from 'lucide-react';
import SpinWheel from './SpinWheel';

const UserDashboard = ({ email, onLogout }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedText, setCopiedText] = useState('');
  const [hoveredDrop, setHoveredDrop] = useState(null);
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [showWheel, setShowWheel] = useState(false);
  const [animatedStats, setAnimatedStats] = useState({
    rep: 0,
    referrals: 0,
    drops: 0
  });
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://api.badge.iopn.io';
  
  // Email masking function
  const maskEmail = (email) => {
    if (!email || !email.includes('@')) return email;
    
    const [local, domain] = email.split('@');
    
    if (local.length <= 3) {
      return `${local[0]}***@${domain}`;
    }
    
    return `${local.slice(0, 3)}***@${domain}`;
  };
  
  useEffect(() => {
    fetchDashboardData();
    // Refresh data every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [email]);

  // Animate numbers when data loads
  useEffect(() => {
    if (dashboardData) {
      animateValue('rep', 0, dashboardData?.total_rep || 0, 2000);
      animateValue('referrals', 0, dashboardData?.user?.successful_referrals || 0, 1500);
      animateValue('drops', 0, dashboardData?.drops?.total || 0, 1800);
    }
  }, [dashboardData]);

  const animateValue = (key, start, end, duration) => {
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    const step = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      
      const value = Math.floor(start + (end - start) * easeOutQuart(progress));
      setAnimatedStats(prev => ({ ...prev, [key]: value }));
      
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    
    requestAnimationFrame(step);
  };

  const easeOutQuart = (x) => {
    return 1 - Math.pow(1 - x, 4);
  };
  
  const fetchDashboardData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/dashboard/${encodeURIComponent(email)}`);
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWheelSpinComplete = (result) => {
    // Refresh dashboard data to show updated REP
    fetchDashboardData();
    
    // Show celebration animation if won
    if (result.rep_earned > 0) {
      // Add celebration effects here if desired
    }
  };
  
  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    setTimeout(() => setCopiedText(''), 2000);
  };
  
  const shareStatsOnTwitter = () => {
    const totalDrops = dashboardData?.drops?.total || 0;
    const bronzeDrops = dashboardData?.drops?.bronze || 0;
    const goldDrops = dashboardData?.drops?.gold || 0;
    const platinumDrops = dashboardData?.drops?.platinum || 0;
    const referrals = dashboardData?.user?.successful_referrals || 0;
    const totalRep = dashboardData?.total_rep || 0;
    
    let text = `I'm officially an @IOPn_io Early Adopter! 🎯\n\n`;
    
    // Add REP if they have any
    if (totalRep > 0) {
      text += `💫 ${totalRep} REP earned\n`;
    }
    
    // Add drop emojis based on what they have
    if (platinumDrops > 0) text += `💎 `;
    if (goldDrops > 0) text += `⭐ `;
    if (bronzeDrops > 0) text += `🏆 `;
    if (totalDrops > 0) text += `\n\n`;
    
    text += `Collected ${totalDrops} drops.\n`;
    text += `Referred ${referrals} builders.\n\n`;
    
    text += `Ready for testnet. Ready for the future.\n\n`;
    text += `The identity revolution starts here 🚀`;
    
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
  };
  
 const getDropDisplay = (tier) => {
  const displays = {
    bronze: {
      image: `${process.env.PUBLIC_URL}/bronze.png`,
      gradient: 'from-orange-400 via-orange-500 to-orange-600',
      glow: 'from-orange-600/30 to-orange-800/30',
      border: 'border-orange-600/50',
      textColor: 'text-orange-400',
      bgColor: 'bg-gray-900/20',
      shadowColor: 'shadow-orange-500/20',
      description: 'Common tier drops',
      animation: 'animate-pulse'
    },
    gold: {
      image: `${process.env.PUBLIC_URL}/gold.png`,
      gradient: 'from-yellow-400 via-yellow-500 to-amber-600',
      glow: 'from-yellow-500/30 to-amber-700/30',
      border: 'border-yellow-500/50',
      textColor: 'text-yellow-400',
      bgColor: 'bg-gray-900/20',
      shadowColor: 'shadow-yellow-500/20',
      description: 'Rare tier drops',
      animation: 'animate-pulse'
    },
    platinum: {
      image: `${process.env.PUBLIC_URL}/platinum.png`, 
      gradient: 'from-purple-400 via-pink-400 to-blue-400',
      glow: 'from-purple-500/30 to-blue-500/30',
      border: 'border-blue-400/50',
      textColor: 'text-blue-400',
      bgColor: 'bg-gray-900/20',
      shadowColor: 'shadow-blue-500/20',
      description: 'Ultra-rare tier drops',
      animation: 'animate-pulse'
    }
  };
  return displays[tier] || displays.bronze;
};
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading your dashboard...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Simple static background - NO ANIMATIONS */}
      <div className="absolute inset-0 w-full h-full bg-black">
        <div className="absolute inset-0 bg-black" />
      </div>
      
      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-gray-800 bg-black">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-3">
                  Early n-Badge Dashboard
                  <span className="px-3 py-1 bg-gray-900 rounded-full text-xs font-medium border border-gray-700">
                    EARLY ADOPTER
                  </span>
                </h1>
                <p className="text-gray-400 mt-1">{email}</p>
              </div>
              <button
                onClick={onLogout}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-all hover:scale-105"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
        
        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Spin Wheel Modal */}
          {showWheel && (
            <SpinWheel 
              email={email}
              onClose={() => setShowWheel(false)}
              onSpinComplete={handleWheelSpinComplete}
            />
          )}

          {/* REP Wheel Promotion - Minimal style */}
          <div className="bg-gray-900/50 border border-[#1d2449] rounded-2xl p-6 mb-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-[#0f112a] rounded-xl flex items-center justify-center">
                  <Dices className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    Spin for REP! 
                    <span className="px-2 py-1 bg-[#0f112a] rounded-full text-xs text-[#4a9eff]">NEW</span>
                  </h3>
                  <p className="text-sm text-gray-300">
                    {dashboardData?.user?.wheel_status?.has_spun 
                      ? `You earned ${dashboardData.user.wheel_status.rep_earned} REP! 🎉`
                      : "One free spin per badge holder - Win up to 1000 REP!"
                    }
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowWheel(true)}
                disabled={dashboardData?.user?.wheel_status?.has_spun}
                className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
                  dashboardData?.user?.wheel_status?.has_spun
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-[#1d2449] text-white hover:bg-[#2a3560] hover:scale-105'
                }`}
              >
                {dashboardData?.user?.wheel_status?.has_spun ? (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Already Spun
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Spin Now
                    <ArrowUp className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Testnet Notice - Minimal style */}
          <div className="bg-gray-900/50 border border-[#1d2449] rounded-2xl p-6 mb-8">
            <div className="flex items-start gap-4">
              <div>
                <Zap className="w-6 h-6 text-[#4a9eff]" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-[#4a9eff] mb-2">Testnet Launching Soon</h3>
                <p className="text-gray-300 text-sm">
                  The Early n-Badge claim has closed. As a badge holder, you're guaranteed priority access to our upcoming testnet. 
                  Your early support has secured your place at the forefront of the identity revolution.
                </p>
              </div>
            </div>
          </div>

          {/* Share Your Stats Section - Minimal style */}
          <div className="bg-gray-900/50 rounded-3xl p-6 mb-8 border border-[#1d2449]">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-[#0f112a] rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Share Your Early Adopter Status</h3>
                  <p className="text-sm text-gray-400">Let the world know you were here first</p>
                </div>
              </div>
              <button
                onClick={shareStatsOnTwitter}
                className="px-6 py-3 bg-white text-black hover:bg-gray-200 rounded-xl font-medium transition-all flex items-center gap-2 hover:scale-105"
              >
                <Twitter className="w-5 h-5" />
                Share My Stats
                <Share2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Stats Overview - Minimal with blue accents */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-[#1d2449]">
              <div className="flex items-center justify-between mb-2">
                <Zap className="w-8 h-8 text-[#4a9eff]" />
                <span className="text-xs text-gray-400 font-medium">TOTAL REP</span>
              </div>
              <p className="text-3xl font-bold text-white">
                {animatedStats.rep}
              </p>
              <p className="text-sm text-gray-400 mt-1">Reputation points</p>
            </div>

            <div className="bg-gray-900/50 rounded-2xl p-6 border border-[#1d2449]">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle className="w-8 h-8 text-green-400" />
                <span className="text-xs text-gray-400 font-medium">FINAL REFERRALS</span>
              </div>
             <p className="text-3xl font-bold text-green-400">{animatedStats.referrals}</p>
              <p className="text-sm text-gray-400 mt-1">Badges claimed</p>
            </div>
            
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-[#1d2449]">
              <div className="flex items-center justify-between mb-2">
                <Gift className="w-8 h-8 text-[#4a9eff]" />
                <span className="text-xs text-gray-400 font-medium">DROPS EARNED</span>
              </div>
              <p className="text-3xl font-bold text-[#4a9eff]">{animatedStats.drops}</p>
              <p className="text-sm text-gray-400 mt-1">Total collected</p>
            </div>
            
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-[#1d2449]">
              <div className="flex items-center justify-between mb-2">
                <Award className="w-8 h-8 text-white" />
                <span className="text-xs text-gray-400 font-medium">BADGE STATUS</span>
              </div>
              <p className="text-xl font-bold text-green-400">Active</p>
              <p className="text-sm text-gray-400 mt-1">Early Adopter</p>
            </div>
          </div>
          
          {/* Drops Collection - Minimal style */}
          <div className="bg-gray-900/30 rounded-3xl p-8 border border-[#1d2449]">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-bold">Your Drop Collection</h2>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Gift className="w-4 h-4" />
                Total: {dashboardData?.drops?.total || 0} drops
              </div>
            </div>
            
            {/* Drop Cards with minimal styling */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
  {['bronze', 'gold', 'platinum'].map((tier) => {
    const dropDisplay = getDropDisplay(tier);
    const count = dashboardData?.drops?.[tier] || 0;
    
    return (
      <div 
        key={tier}
        className="relative group cursor-pointer transition-all duration-500"
        onMouseEnter={() => setHoveredDrop(tier)}
        onMouseLeave={() => setHoveredDrop(null)}
      >
        <div className={`${dropDisplay.bgColor} rounded-2xl p-6 border ${dropDisplay.border} ${hoveredDrop === tier ? 'transform -translate-y-2' : ''} transition-all`}>
          {/* Content */}
          <div className="relative z-10">
            <div className="w-20 h-20 mx-auto mb-4">
              <img 
                src={dropDisplay.image} 
                alt={`${tier} drop`}
                className="w-full h-full object-contain"
              />
            </div>
            
            <h3 className={`text-xl font-bold capitalize mb-1 text-center ${dropDisplay.textColor}`}>
              {tier}
            </h3>
            
            <p className="text-4xl font-bold text-white text-center mb-3">
              {count}
            </p>
            
            <p className="text-xs text-gray-500 text-center">{dropDisplay.description}</p>
          </div>
        </div>
      </div>
    );
  })}
</div>
            
            {/* Recent Activity */}
{dashboardData?.drops?.recent?.length > 0 && (
  <div className="bg-black/40 rounded-2xl p-6">
    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
      <Clock className="w-5 h-5 text-gray-400" />
      Your Earned Drops
    </h3>
    <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
      {dashboardData.drops.recent.slice(0, 10).map((drop, index) => {
        const dropDisplay = getDropDisplay(drop.drop_tier);
        
        return (
          <div 
            key={index} 
            className="bg-gray-800/50 rounded-xl p-4 flex items-center justify-between border border-[#1d2449] hover:bg-gray-800/70 transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12">
                <img 
                  src={dropDisplay.image} 
                  alt={`${drop.drop_tier} drop`}
                  className="w-full h-full object-contain"
                />
              </div>
              <div>
                <p className="font-semibold">
                  <span className={`capitalize ${dropDisplay.textColor}`}>{drop.drop_tier} Drop</span>
                  {index === 0 && <span className="text-xs ml-2 px-2 py-1 bg-green-500/20 text-green-400 rounded-full">LATEST</span>}
                </p>
                <p className="text-sm text-gray-400">
                  From: {maskEmail(drop.earned_from_email)}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">
                {new Date(drop.earned_at).toLocaleDateString()}
              </p>
              <p className="text-xs text-gray-500">
                {new Date(drop.earned_at).toLocaleTimeString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  </div>
)}
          </div>
          
          {/* NFT Launch Notice - Minimal style */}
          <div className="bg-gray-900/50 rounded-3xl p-8 border border-[#1d2449] relative">
            <div className="relative z-10">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <div className="w-16 h-16 bg-[#0f112a] rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold mb-3">
                    What's Next: Testnet & Origin NFT
                  </h3>
                  <p className="text-gray-300 mb-4">
                    Your journey as an Early Adopter continues. Get ready for exclusive testnet access where your 
                    drops will unlock special abilities. The Origin NFT will immortalize your early support on-chain.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <div className="px-4 py-2 bg-[#0f112a] rounded-lg border border-[#1d2449]">
                      <p className="text-xs text-gray-400">Your Drops</p>
                      <p className="font-bold">{dashboardData?.drops?.total || 0} Total</p>
                    </div>
                    <div className="px-4 py-2 bg-[#0f112a] rounded-lg border border-[#1d2449]">
                      <p className="text-xs text-gray-400">Testnet Access</p>
                      <p className="font-bold text-green-400">Priority</p>
                    </div>
                    <div className="px-4 py-2 bg-[#0f112a] rounded-lg border border-[#1d2449]">
                      <p className="text-xs text-gray-400">Badge Status</p>
                      <p className="font-bold text-[#4a9eff]">Early Adopter</p>
                    </div>
                    <div className="px-4 py-2 bg-[#0f112a] rounded-lg border border-[#1d2449]">
                      <p className="text-xs text-gray-400">Total REP</p>
                      <p className="font-bold text-[#4a9eff]">{dashboardData?.total_rep || 0}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.3);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1d2449;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #2a3560;
        }
      `}</style>
    </div>
  );
};

export default UserDashboard;