// frontend/src/components/UserDashboard.jsx
import React, { useState, useEffect } from 'react';
import { Copy, Users, Gift, Loader2, ExternalLink, CheckCircle, Trophy, Sparkles, Star, TrendingUp, Share2, Twitter, LogOut, Zap, Clock, Award, BarChart3 } from 'lucide-react';

const UserDashboard = ({ email, onLogout }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedText, setCopiedText] = useState('');
  const [hoveredDrop, setHoveredDrop] = useState(null);
  const [showShareMenu, setShowShareMenu] = useState(false);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://api.badge.iopn.io';
  
  // Email masking function - moved to component level
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
  
  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    setTimeout(() => setCopiedText(''), 2000);
  };
  
  const getReferralLink = () => {
    return `https://badge.iopn.io/?ref=${dashboardData?.user?.referral_code || ''}`;
  };
  
  const shareStatsOnTwitter = () => {
    const totalDrops = dashboardData?.drops?.total || 0;
    const bronzeDrops = dashboardData?.drops?.bronze || 0;
    const goldDrops = dashboardData?.drops?.gold || 0;
    const platinumDrops = dashboardData?.drops?.platinum || 0;
    const referrals = dashboardData?.user?.successful_referrals || 0;
    
    let text = `🎯 My @IOPn_io Early n-Badge Stats:\n\n`;
    text += `📊 Total Drops: ${totalDrops}\n`;
    
    if (platinumDrops > 0) text += `💎 Platinum: ${platinumDrops}\n`;
    if (goldDrops > 0) text += `⭐ Gold: ${goldDrops}\n`;
    if (bronzeDrops > 0) text += `🏆 Bronze: ${bronzeDrops}\n`;
    
    text += `\n👥 Successful Referrals: ${referrals}\n`;
    text += `\n🚀 Join the identity revolution:\n${getReferralLink()}\n\n`;
    
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
  };
  
  const shareReferralOnTwitter = () => {
    const text = `Join me in the @IOPn_io identity revolution! 🚀\n\nClaim your Early n-Badge and earn exclusive drops:\n${getReferralLink()}`;
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
      bgColor: 'bg-orange-900/20',
      shadowColor: 'shadow-orange-500/20',
      description: 'Common tier drops'
    },
    gold: {
      image: `${process.env.PUBLIC_URL}/gold.png`,
      gradient: 'from-yellow-400 via-yellow-500 to-amber-600',
      glow: 'from-yellow-500/30 to-amber-700/30',
      border: 'border-yellow-500/50',
      textColor: 'text-yellow-400',
      bgColor: 'bg-yellow-900/20',
      shadowColor: 'shadow-yellow-500/20',
      description: 'Rare tier drops'
    },
    platinum: {
      image: `${process.env.PUBLIC_URL}/platinum.png`, 
      gradient: 'from-purple-400 via-pink-400 to-blue-400',
      glow: 'from-purple-500/30 to-blue-500/30',
      border: 'border-purple-500/50',
      textColor: 'text-purple-400',
      bgColor: 'bg-purple-900/20',
      shadowColor: 'shadow-purple-500/20',
      description: 'Ultra-rare tier drops'
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
      {/* Animated Background */}
      <div className="absolute inset-0 w-full h-full bg-black">
        <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-50">
          <source src={`${process.env.PUBLIC_URL}/background-video.mp4`} type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-black/60" />
      </div>
      
      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-gray-800 bg-black/50 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-3">
                  Early n-Badge Dashboard
                  <span className="px-3 py-1 bg-white/10 rounded-full text-xs font-medium border border-white/20">
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
          {/* Share Your Stats Section */}
          <div className="bg-gray-900/50 rounded-3xl p-6 mb-8 border border-gray-800 backdrop-blur-sm">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Share Your Achievement</h3>
                  <p className="text-sm text-gray-400">Show off your Early n-Badge stats on X</p>
                </div>
              </div>
              <button
                onClick={shareStatsOnTwitter}
                className="px-6 py-3 bg-white text-black hover:bg-gray-200 rounded-xl font-medium transition-all flex items-center gap-2 group hover:scale-105"
              >
                <Twitter className="w-5 h-5" />
                Share My Stats
                <Share2 className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
          
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle className="w-8 h-8 text-green-400" />
                <span className="text-xs text-gray-400 font-medium">SUCCESSFUL REFERRALS</span>
              </div>
             <p className="text-3xl font-bold">{dashboardData?.user?.successful_referrals || 0}</p>
              <p className="text-sm text-gray-400 mt-1">Badges claimed</p>
            </div>
            
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <Gift className="w-8 h-8 text-blue-400" />
                <span className="text-xs text-gray-400 font-medium">DROPS EARNED</span>
              </div>
              <p className="text-3xl font-bold">{dashboardData?.drops?.total || 0}</p>
              <p className="text-sm text-gray-400 mt-1">Total collected</p>
            </div>
            
            <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <Award className="w-8 h-8 text-white" />
                <span className="text-xs text-gray-400 font-medium">BADGE STATUS</span>
              </div>
              <p className="text-xl font-bold text-green-400">Active</p>
              <p className="text-sm text-gray-400 mt-1">Early Adopter</p>
            </div>
          </div>
          
          {/* Referral Section */}
          <div className="bg-gray-900/30 backdrop-blur-sm rounded-3xl p-8 mb-8 border border-gray-800">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
              <h2 className="text-2xl font-bold mb-4 sm:mb-0">Referral Program</h2>
              <button
                onClick={shareReferralOnTwitter}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors flex items-center gap-2"
              >
                <Twitter className="w-4 h-4" />
                Share Link
              </button>
            </div>
            
            <div className="bg-black/40 rounded-2xl p-5 mb-6">
              <p className="text-sm text-gray-400 mb-3">Your unique referral link:</p>
              <div className="flex items-center gap-3">
                <code className="flex-1 text-sm sm:text-base text-gray-300 break-all bg-black/50 rounded-lg px-4 py-3">
                  {getReferralLink()}
                </code>
                <button
                  onClick={() => copyToClipboard(getReferralLink(), 'referral')}
                  className="flex-shrink-0 p-3 bg-white/10 hover:bg-white/20 rounded-lg transition-all hover:scale-105"
                >
                  {copiedText === 'referral' ? 
                    <CheckCircle className="w-5 h-5 text-green-400" /> : 
                    <Copy className="w-5 h-5" />
                  }
                </button>
              </div>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-3">
                <Award className="w-6 h-6 text-white" />
                <div>
                  <p className="font-medium">Earn drops for each successful referral!</p>
                  <p className="text-sm text-gray-400">When your referrals claim their badge, you'll receive random tier drops</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Drops Collection */}
          <div className="bg-gray-900/30 backdrop-blur-sm rounded-3xl p-8 border border-gray-800">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-bold">Drop Collection</h2>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Gift className="w-4 h-4" />
                Total: {dashboardData?.drops?.total || 0} drops
              </div>
            </div>
            
            {/* Drop Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
  {['bronze', 'gold', 'platinum'].map((tier) => {
    const dropDisplay = getDropDisplay(tier);
    const count = dashboardData?.drops?.[tier] || 0;
    
    return (
      <div 
        key={tier}
        className={`relative group cursor-pointer transition-all duration-500 ${
          hoveredDrop === tier ? 'transform -translate-y-2' : ''
        }`}
        onMouseEnter={() => setHoveredDrop(tier)}
        onMouseLeave={() => setHoveredDrop(null)}
      >
        <div className={`${dropDisplay.bgColor} rounded-2xl p-6 border ${dropDisplay.border} backdrop-blur-sm overflow-hidden`}>
          {/* Animated Glow */}
          <div className={`absolute inset-0 bg-gradient-to-br ${dropDisplay.glow} rounded-2xl blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
          
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute -top-24 -right-24 w-48 h-48 bg-white rounded-full blur-3xl" />
            <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-white rounded-full blur-3xl" />
          </div>
          
          {/* Content */}
          <div className="relative z-10">
            {/* Updated to use image instead of icon */}
            <div className="w-20 h-20 mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
              <img 
                src={dropDisplay.image} 
                alt={`${tier} drop`}
                className="w-full h-full object-contain drop-shadow-2xl"
              />
            </div>
            
            <h3 className={`text-xl font-bold capitalize mb-1 text-center ${dropDisplay.textColor}`}>
              {tier}
            </h3>
            
            <p className="text-4xl font-bold text-white text-center mb-3">{count}</p>
            
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
      Recent Drops
    </h3>
    <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
      {dashboardData.drops.recent.slice(0, 5).map((drop, index) => {
        const dropDisplay = getDropDisplay(drop.drop_tier);
        
        return (
          <div 
            key={index} 
            className="bg-gray-800/50 rounded-xl p-4 flex items-center justify-between group hover:bg-gray-800/70 transition-all duration-300 border border-gray-700/50"
          >
            <div className="flex items-center gap-4">
              {/* Updated to use image instead of icon */}
              <div className="w-12 h-12 group-hover:scale-110 transition-transform">
                <img 
                  src={dropDisplay.image} 
                  alt={`${drop.drop_tier} drop`}
                  className="w-full h-full object-contain drop-shadow-lg"
                />
              </div>
              <div>
                <p className="font-semibold">
                  <span className={`capitalize ${dropDisplay.textColor}`}>{drop.drop_tier} Drop</span>
                  <span className="text-xs ml-2 px-2 py-1 bg-green-500/20 text-green-400 rounded-full">NEW</span>
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
          
          {/* NFT Launch Notice */}
          <div className="bg-gray-900/50 rounded-3xl p-8 border border-gray-800 backdrop-blur-sm relative overflow-hidden">
            <div className="relative z-10">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <div className="w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold mb-3">
                    Origin NFT Launching Soon
                  </h3>
                  <p className="text-gray-300 mb-4">
                    Your collected drops will unlock exclusive rewards when you mint your Origin NFT. 
                    Early badge holders receive priority access and special benefits!
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <div className="px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
                      <p className="text-xs text-gray-400">Your Drops</p>
                      <p className="font-bold">{dashboardData?.drops?.total || 0} Total</p>
                    </div>
                    <div className="px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
                      <p className="text-xs text-gray-400">Status</p>
                      <p className="font-bold text-green-400">Priority Access</p>
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
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3);
        }
      `}</style>
    </div>
  );
};

export default UserDashboard;