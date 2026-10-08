"use client";

import React, { useState, useEffect } from "react";
import { GraduationCap, ShieldCheck, Cpu, Database } from "lucide-react";

interface SplashScreenProps {
  isReady: boolean;
  onFinished?: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({
  isReady,
  onFinished,
}) => {
  const [mounted, setMounted] = useState(true);
  const [fading, setFading] = useState(false);
  const [stepText, setStepText] = useState("Initializing Tutor Core...");
  const [progress, setProgress] = useState(15);

  useEffect(() => {
    // Step progression timer
    const t1 = setTimeout(() => {
      setProgress(45);
      setStepText("Verifying Local Vector Index & Database...");
    }, 400);

    const t2 = setTimeout(() => {
      setProgress(75);
      setStepText("Connecting to Nemotron 3 Nano Cloud...");
    }, 800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  useEffect(() => {
    if (isReady && progress >= 75) {
      setProgress(100);
      setStepText("Workstation Ready");
      const timer = setTimeout(() => {
        setFading(true);
        setTimeout(() => {
          setMounted(false);
          onFinished?.();
        }, 500);
      }, 400);
      return () => clearTimeout(timer);
    } else if (isReady) {
      const timer = setTimeout(() => {
        setProgress(100);
        setStepText("Workstation Ready");
        setTimeout(() => {
          setFading(true);
          setTimeout(() => {
            setMounted(false);
            onFinished?.();
          }, 500);
        }, 400);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isReady, progress, onFinished]);

  if (!mounted) return null;

  const handleDismiss = () => {
    setFading(true);
    setTimeout(() => {
      setMounted(false);
      onFinished?.();
    }, 300);
  };

  return (
    <div
      onClick={handleDismiss}
      className={`fixed inset-0 z-50 flex flex-col items-center justify-between p-8 bg-black text-white transition-opacity duration-500 select-none cursor-pointer ${
        fading ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* Top Bar Branding */}
      <div className="w-full max-w-4xl flex items-center justify-between text-xs text-zinc-400 font-mono tracking-wider pt-2">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-white" />
          <span>STUDYLENS AI • v1.0</span>
        </div>
        <span className="text-[11px] text-zinc-500 hover:text-white transition-colors">
          Click anywhere to skip
        </span>
      </div>

      {/* Center Monogram & Title */}
      <div className="flex flex-col items-center justify-center text-center max-w-md w-full my-auto space-y-6">
        {/* Monogram Box - Pure Black & White, No Glow */}
        <div className="w-20 h-20 rounded-2xl bg-zinc-950 border border-zinc-800 flex items-center justify-center shadow-lg">
          <GraduationCap className="w-9 h-9 text-white" />
        </div>

        {/* Brand Text */}
        <div className="space-y-1.5">
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
            StudyLens AI
          </h1>
          <p className="text-xs md:text-sm text-zinc-400 font-medium">
            Grounded Academic AI Tutor & Research Workspace
          </p>
        </div>

        {/* Progress & Micro-Indicator */}
        <div className="w-full max-w-xs space-y-2 pt-2">
          {/* Track */}
          <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
            <div
              className="h-full bg-white transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
            <span className="truncate">{stepText}</span>
            <span className="ml-2 font-semibold text-white">{progress}%</span>
          </div>
        </div>
      </div>

      {/* Bottom Architecture Badges */}
      <div className="w-full max-w-md flex items-center justify-center gap-6 text-[11px] text-zinc-400 font-medium pb-2 border-t border-zinc-900 pt-4">
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-zinc-300" />
          <span>Nemotron 3 Nano</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-zinc-300" />
          <span>Vector Index</span>
        </div>
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-zinc-300" />
          <span>Grounded Citations</span>
        </div>
      </div>
    </div>
  );
};
