import React, { useState, useEffect } from 'react';
import { Sparkles, Loader2, X, Zap, Trophy, Star, Dices, ArrowUp, CheckCircle, Gem } from 'lucide-react';

const SpinWheel = ({ email, onClose, onSpinComplete }) => {
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [currentRotation, setCurrentRotation] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [spinResult, setSpinResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [winningIndex, setWinningIndex] = useState(null);
  const [isHovering, setIsHovering] = useState(false);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://api.badge.iopn.io';
  
  // Enhanced color scheme with gradients
  const segments = [
    { value: 0, label: "Try Again", color: "#1a1a2e", textColor: "#666", icon: "😅", odds: 15 },
    { value: 10, label: "10 REP", color: "#16213e", textColor: "#94a3b8", icon: "⚡", odds: 20 },
    { value: 25, label: "25 REP", color: "#1e3a5f", textColor: "#94a3b8", icon: "⚡", odds: 18 },
    { value: 50, label: "50 REP", color: "#2563eb", textColor: "#e0e7ff", icon: "✨", odds: 15 },
    { value: 100, label: "100 REP", color: "#3b82f6", textColor: "#ffffff", icon: "💎", odds: 12 },
    { value: 250, label: "250 REP", color: "#60a5fa", textColor: "#ffffff", icon: "💎", odds: 8 },
    { value: 500, label: "500 REP", color: "#818cf8", textColor: "#ffffff", icon: "🏆", odds: 7 },
    { value: 750, label: "750 REP", color: "#a78bfa", textColor: "#ffffff", icon: "👑", odds: 4 },
    { value: 1000, label: "1000 REP", color: "#10b981", textColor: "#ffffff", icon: "🚀", odds: 1 },
  ];

  const degreesPerSegment = 360 / segments.length;
  const totalOdds = segments.reduce((sum, seg) => sum + seg.odds, 0);
  
  const getSegmentAtRotation = (rotation) => {
    let normalizedRotation = ((rotation % 360) + 360) % 360;
    let pointerAngle = (360 - normalizedRotation) % 360;
    let segmentIndex = Math.floor(pointerAngle / degreesPerSegment);
    segmentIndex = segmentIndex % segments.length;
    return segmentIndex;
  };
  
  const calculateRotationForSegment = (targetIndex, withRandomness = true) => {
    const segmentStartAngle = targetIndex * degreesPerSegment;
    
    let targetAngle;
    if (withRandomness) {
      const margin = degreesPerSegment * 0.1;
      targetAngle = segmentStartAngle + margin + (Math.random() * (degreesPerSegment - 2 * margin));
    } else {
      targetAngle = segmentStartAngle + (degreesPerSegment / 2);
    }
    
    return -targetAngle;
  };
  
  useEffect(() => {
    checkSpinStatus();
  }, [email]);
  
  const checkSpinStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/wheel/status/${encodeURIComponent(email)}`);
      const data = await response.json();
      
      if (data.has_spun) {
        setHasSpun(true);
        setSpinResult(data.spin_data);
        setShowResult(true);
        
        const winIdx = segments.findIndex(s => s.value === data.spin_data.rep_earned);
        if (winIdx !== -1) {
          setWinningIndex(winIdx);
          const winningRotation = calculateRotationForSegment(winIdx, true);
          setCurrentRotation(winningRotation);
        }
      }
    } catch (error) {
      console.error('Error checking spin status:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSpin = async () => {
    if (isSpinning || hasSpun) return;
    
    setIsSpinning(true);
    
    try {
      const response = await fetch(`${API_URL}/api/wheel/spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        const winIdx = segments.findIndex(s => s.value === data.rep_earned);
        
        if (winIdx === -1) {
          console.error('Invalid value from server:', data.rep_earned);
          setIsSpinning(false);
          return;
        }
        
        setWinningIndex(winIdx);
        
        const targetRotation = calculateRotationForSegment(winIdx, true);
        const extraSpins = 5 + Math.floor(Math.random() * 3);
        const totalRotation = targetRotation - (extraSpins * 360);
        
        setCurrentRotation(totalRotation);
        setSpinResult(data);
        
        setTimeout(() => {
          setIsSpinning(false);
          setShowResult(true);
          setHasSpun(true);
          
          if (onSpinComplete) {
            onSpinComplete(data);
          }
        }, 4000);
      }
    } catch (error) {
      console.error('Error spinning wheel:', error);
      setIsSpinning(false);
    }
  };

  const createSegments = () => {
    return segments.map((segment, index) => {
      const startAngle = index * degreesPerSegment - 90;
      const endAngle = startAngle + degreesPerSegment;
      
      const startRad = (startAngle * Math.PI) / 180;
      const endRad = (endAngle * Math.PI) / 180;
      
      const x1 = 150 + 140 * Math.cos(startRad);
      const y1 = 150 + 140 * Math.sin(startRad);
      const x2 = 150 + 140 * Math.cos(endRad);
      const y2 = 150 + 140 * Math.sin(endRad);
      
      const path = `M 150 150 L ${x1} ${y1} A 140 140 0 0 1 ${x2} ${y2} Z`;
      
      const textAngle = startAngle + degreesPerSegment / 2;
      const textRad = (textAngle * Math.PI) / 180;
      const textX = 150 + 100 * Math.cos(textRad);
      const textY = 150 + 100 * Math.sin(textRad);
      const iconX = 150 + 70 * Math.cos(textRad);
      const iconY = 150 + 70 * Math.sin(textRad);
      
      const isWinner = winningIndex === index && showResult;
      
      return (
        <g key={index}>
          <defs>
            <radialGradient id={`gradient-${index}`}>
              <stop offset="0%" stopColor={segment.color} stopOpacity="1" />
              <stop offset="100%" stopColor={segment.color} stopOpacity="0.7" />
            </radialGradient>
          </defs>
          
          <path
            d={path}
            fill={`url(#gradient-${index})`}
            stroke={isWinner ? "#ffffff" : "rgba(255,255,255,0.1)"}
            strokeWidth={isWinner ? "2" : "0.5"}
            className={isWinner ? "animate-pulse drop-shadow-lg" : ""}
            style={{
              filter: isWinner ? 'brightness(1.3)' : 'brightness(1)',
              transition: 'all 0.3s ease'
            }}
          />
          
          <text
            x={iconX}
            y={iconY}
            fontSize="20"
            textAnchor="middle"
            dominantBaseline="middle"
            transform={`rotate(${textAngle + 90} ${iconX} ${iconY})`}
          >
            {segment.icon}
          </text>
          
          <text
            x={textX}
            y={textY}
            fill={segment.textColor}
            fontSize="12"
            fontWeight="700"
            textAnchor="middle"
            dominantBaseline="middle"
            transform={`rotate(${textAngle + 90} ${textX} ${textY})`}
            style={{
              textShadow: '0 1px 2px rgba(0,0,0,0.5)',
              letterSpacing: '0.5px'
            }}
          >
            {segment.label}
          </text>
        </g>
      );
    });
  };
  
  if (loading) {
    return (
      <div className="fixed inset-0 bg-gradient-to-b from-gray-900 via-black to-black z-50 flex items-center justify-center">
        <div className="relative">
          <div className="absolute inset-0 animate-ping">
            <Dices className="w-16 h-16 text-blue-500/30" />
          </div>
          <Dices className="w-16 h-16 text-blue-500 animate-spin" />
        </div>
      </div>
    );
  }
  
  return (
    <div className="fixed inset-0 bg-gradient-to-b from-gray-900/95 via-black/95 to-black/95 backdrop-blur-xl z-50 overflow-y-auto">
      <div className="min-h-full flex items-center justify-center p-4">
        {/* Animated background particles */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute animate-float"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${15 + Math.random() * 10}s`
              }}
            >
              <div className="w-1 h-1 bg-blue-500/20 rounded-full blur-sm" />
            </div>
          ))}
        </div>
        
        <div className="relative bg-gradient-to-b from-gray-900 to-gray-950 border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-full max-w-5xl shadow-2xl my-4">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-600/10 via-purple-600/10 to-blue-600/10 blur-3xl" />
        
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl bg-black/50 hover:bg-black/70 transition-all border border-gray-700 hover:border-gray-600 z-10"
        >
          <X className="w-5 h-5 text-gray-400 hover:text-white" />
        </button>
        
        <div className="relative text-center mb-4">
          <h2 className="text-2xl sm:text-3xl font-black mb-1 bg-gradient-to-r from-blue-400 via-purple-400 to-blue-400 bg-clip-text text-transparent animate-gradient">
            SPIN FOR REP
          </h2>
          <p className="text-gray-400 text-xs sm:text-sm uppercase tracking-wider">
            {hasSpun ? "✨ Already Claimed ✨" : "⚡ One Spin • Maximum Luck ⚡"}
          </p>
        </div>
        
        {/* Main Layout Container */}
        <div className="flex flex-col gap-6">
          {/* Top Section - Wheel and Controls Side by Side */}
          <div className="flex flex-col lg:flex-row items-center lg:items-start gap-4 sm:gap-6 lg:gap-8 justify-center">
            {/* Left side - Wheel */}
            <div className="flex-shrink-0">
              <div className="relative w-[260px] h-[260px] sm:w-[320px] sm:h-[320px]">
                <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-3xl animate-pulse" />
                <div className="absolute inset-4 bg-purple-500/10 rounded-full blur-2xl animate-pulse" style={{ animationDelay: '0.5s' }} />
                
                <div className="relative w-full h-full flex items-center justify-center">
                  <div className="absolute inset-0 rounded-full border-2 border-blue-500/30 animate-spin-slow" />
                  
                  <svg
                    viewBox="0 0 320 320"
                    className="w-[240px] h-[240px] sm:w-[300px] sm:h-[300px] drop-shadow-2xl"
                    style={{
                      transform: `rotate(${currentRotation}deg)`,
                      transition: isSpinning ? 'transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'transform 0.5s ease-out',
                      filter: isSpinning ? 'blur(1px)' : 'blur(0px)'
                    }}
                  >
                    <circle cx="160" cy="160" r="155" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" />
                    <circle cx="160" cy="160" r="145" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                    
                    <g transform="translate(10, 10)">
                      {createSegments()}
                    </g>
                    
                    <defs>
                      <radialGradient id="centerGradient">
                        <stop offset="0%" stopColor="#1e293b" />
                        <stop offset="100%" stopColor="#0f172a" />
                      </radialGradient>
                    </defs>
                    
                    <circle cx="160" cy="160" r="40" fill="url(#centerGradient)" stroke="#3b82f6" strokeWidth="2" />
                    <text x="160" y="155" fill="#60a5fa" fontSize="16" fontWeight="bold" textAnchor="middle" dominantBaseline="middle">
                      REP
                    </text>
                    <text x="160" y="172" fill="#60a5fa" fontSize="10" textAnchor="middle" dominantBaseline="middle" opacity="0.7">
                      WHEEL
                    </text>
                  </svg>
                  
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 z-10">
                    <div className="relative">
                      <div className="absolute inset-0 bg-white/50 blur-xl animate-pulse" />
                      
                      <svg width="40" height="40" viewBox="0 0 50 50" className="w-8 h-8 sm:w-10 sm:h-10 drop-shadow-2xl">
                        <defs>
                          <linearGradient id="pointerGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="#60a5fa" />
                            <stop offset="100%" stopColor="#3b82f6" />
                          </linearGradient>
                        </defs>
                        <path 
                          d="M25 8 L35 30 L25 25 L15 30 Z" 
                          fill="url(#pointerGradient)" 
                          stroke="#ffffff" 
                          strokeWidth="1.5"
                        />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Right side - Controls and Result */}
            <div className="flex-1 w-full lg:max-w-md flex flex-col justify-center">
              {!showResult ? (
                <button
                  onClick={handleSpin}
                  disabled={isSpinning || hasSpun}
                  onMouseEnter={() => setIsHovering(true)}
                  onMouseLeave={() => setIsHovering(false)}
                  className={`relative w-full py-4 rounded-xl font-black text-lg transition-all flex items-center justify-center gap-3 overflow-hidden ${
                    isSpinning || hasSpun
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:scale-105 shadow-lg hover:shadow-blue-500/25'
                  }`}
                >
                  {!isSpinning && !hasSpun && (
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 animate-gradient opacity-50" />
                  )}
                  
                  <div className="relative flex items-center gap-3">
                    {isSpinning ? (
                      <>
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span className="animate-pulse">SPINNING...</span>
                      </>
                    ) : hasSpun ? (
                      <>
                        <CheckCircle className="w-6 h-6" />
                        <span>ALREADY SPUN</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-6 h-6" />
                        <span>SPIN NOW</span>
                        <Sparkles className={`w-6 h-6 ${isHovering ? 'animate-spin' : ''}`} />
                      </>
                    )}
                  </div>
                </button>
              ) : (
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl blur-xl" />
                  
                  <div className="relative bg-gradient-to-b from-gray-900 to-black border border-blue-500/30 rounded-xl p-6">
                    {spinResult?.rep_earned > 0 ? (
                      <div className="text-center">
                        <div className="mb-3 relative inline-block">
                          <Trophy className="w-16 h-16 text-yellow-400 animate-bounce mx-auto" />
                          <Sparkles className="absolute top-0 right-0 w-5 h-5 text-yellow-300 animate-ping" />
                        </div>
                        
                        <h3 className="text-2xl font-black mb-2 bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">
                          WINNER!
                        </h3>
                        
                        <div className="my-4">
                          <p className="text-5xl font-black text-white mb-1">
                            {spinResult.rep_earned}
                          </p>
                          <p className="text-xl font-bold text-blue-400">REP EARNED</p>
                        </div>
                        
                        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-2.5 mt-4">
                          <p className="text-gray-300 text-sm flex items-center justify-center gap-2">
                            <Gem className="w-4 h-4 text-blue-400" />
                            Claimable at Origin NFT launch
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center">
                        <div className="text-6xl mb-3">😅</div>
                        <h3 className="text-xl font-bold mb-2 text-white">Better Luck Next Time!</h3>
                        <p className="text-gray-400 text-sm">
                          You're still an Early Adopter with all your collected drops!
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Bottom Section - Probabilities Full Width */}
          <div className="w-full pb-4">
            <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-3 sm:p-4">
              <div className="flex items-center justify-center gap-2 mb-3 sm:mb-4">
                <Star className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
                <span className="text-sm sm:text-base font-semibold text-gray-200">Win Probabilities</span>
                <Star className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
              </div>
              
              <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-1.5 sm:gap-2">
                {segments.map((segment, index) => {
                  const percentage = ((segment.odds / totalOdds) * 100).toFixed(0);
                  return (
                    <div 
                      key={`prob-${index}`}
                      className="flex flex-col items-center justify-center p-2 sm:p-3 bg-black/40 rounded-lg border border-gray-800 hover:border-blue-500/30 transition-all"
                    >
                      <span className="text-lg sm:text-2xl mb-0.5 sm:mb-1">{segment.icon}</span>
                      <span 
                        className="text-[10px] sm:text-xs font-bold mb-0.5 sm:mb-1"
                        style={{ color: segment.value === 0 ? '#666' : segment.color }}
                      >
                        {segment.label}
                      </span>
                      <span className="text-xs sm:text-sm text-gray-400 font-mono">
                        {percentage}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          33% { transform: translateY(-20px) translateX(10px); }
          66% { transform: translateY(20px) translateX(-10px); }
        }
        
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .animate-float {
          animation: float 15s ease-in-out infinite;
        }
        
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
        
        .animate-spin-slow {
          animation: spin-slow 20s linear infinite;
        }
      `}</style>
    </div>
        </div>
  );
};

export default SpinWheel;