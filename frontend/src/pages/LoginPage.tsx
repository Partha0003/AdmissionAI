import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Lock, Mail, AlertCircle, ArrowRight, Sparkles, UserCheck } from 'lucide-react';
import { authService } from '../services/auth';
import { institutionConfig } from '../config/institution';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const auth = await authService.login(email, password);
      if (auth.role === 'STUDENT') {
        navigate('/student/dashboard');
      } else {
        navigate('/admin/dashboard');
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Authentication failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="w-full max-w-md">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-100 p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-50 text-blue-600 mb-3 border border-blue-100">
            <UserCheck className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Portal Authentication
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Access your secure {institutionConfig.name} admission workspace
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start space-x-2 text-rose-700 text-xs">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Email / Application Identity
            </label>
            <div className="relative rounded-lg shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="text"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. karthik.xyz2026001@demo.admissionai.local"
                className="block w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 bg-white placeholder-slate-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Secure Password
            </label>
            <div className="relative rounded-lg shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="block w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 bg-white placeholder-slate-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 shadow-md shadow-blue-500/20 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <span className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Signing In...</span>
              </span>
            ) : (
              <>
                <span>Sign In to Portal</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Account Activation Link */}
        <div className="mt-4 p-3 rounded-xl bg-emerald-50/80 border border-emerald-200 text-center">
          <p className="text-xs font-semibold text-emerald-900">First Time Candidate with TNEA Allotment?</p>
          <Link
            to="/activate"
            className="inline-flex items-center space-x-1 text-xs font-bold text-emerald-700 hover:text-emerald-800 mt-1"
          >
            <span>Activate Account with Token</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Demo Credentials Quick-Select Pill Box */}
        <div className="mt-6 pt-6 border-t border-slate-100">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-500" />
            Quick Demo Persona Login
          </p>

          <div className="space-y-1.5">
            <button
              type="button"
              onClick={() => handleQuickFill('karthik.xyz2026001@demo.admissionai.local', 'Student@1234')}
              className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200/80 hover:border-blue-300 text-xs transition-colors flex items-center justify-between"
            >
              <div>
                <span className="font-semibold text-slate-800">Student 1: Karthikeyan S</span>
                <p className="text-[10px] text-slate-500 font-mono">XYZ2026001 &bull; ACTIVATED</p>
              </div>
              <span className="text-[10px] font-semibold text-blue-600 bg-white px-2 py-0.5 rounded border border-blue-200">
                Use
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('ananya.xyz2026002@demo.admissionai.local', 'Student@1234')}
              className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200/80 hover:border-blue-300 text-xs transition-colors flex items-center justify-between"
            >
              <div>
                <span className="font-semibold text-slate-800">Student 2: Ananya Ramesh</span>
                <p className="text-[10px] text-slate-500 font-mono">XYZ2026002 &bull; APPLICATION IN PROGRESS</p>
              </div>
              <span className="text-[10px] font-semibold text-blue-600 bg-white px-2 py-0.5 rounded border border-blue-200">
                Use
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('admin@xyz.edu.demo', 'Admin@1234')}
              className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-purple-50 border border-slate-200/80 hover:border-purple-300 text-xs transition-colors flex items-center justify-between"
            >
              <div>
                <span className="font-semibold text-slate-800">Staff: Admission Admin / Verifier</span>
                <p className="text-[10px] text-slate-500 font-mono">admin@xyz.edu.demo</p>
              </div>
              <span className="text-[10px] font-semibold text-purple-600 bg-white px-2 py-0.5 rounded border border-purple-200">
                Use
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
