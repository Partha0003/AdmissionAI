import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { KeyRound, Lock, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { authService } from '../services/auth';
import { institutionConfig } from '../config/institution';
import { ActivationResponse } from '../types';

export const ActivationPage: React.FC = () => {
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<ActivationResponse | null>(null);
  const navigate = useNavigate();

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.activateAccount(token.trim(), password);
      setSuccessData(res);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Activation failed. Please ensure your token is valid and has not expired.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleQuickToken = (sampleToken: string) => {
    setToken(sampleToken);
    setPassword('Student@1234');
    setConfirmPassword('Student@1234');
    setError(null);
  };

  return (
    <div className="w-full max-w-md">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-100 p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 mb-3 border border-emerald-100">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Student Account Activation
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            {institutionConfig.name} &bull; Admissions {institutionConfig.academicYear}
          </p>
        </div>

        {successData ? (
          <div className="space-y-5 text-center">
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <h3 className="font-bold text-base text-emerald-950">Account Activated Successfully!</h3>
              <p className="text-xs text-emerald-700 mt-1">
                Welcome, <span className="font-semibold">{successData.student_name}</span> ({successData.tnea_application_number}). Your admission lifecycle is now <strong className="uppercase">ACTIVATED</strong>.
              </p>
            </div>

            <div className="bg-slate-50 rounded-lg p-3 text-left text-xs space-y-1.5 border border-slate-200">
              <div className="flex justify-between">
                <span className="text-slate-500">TNEA Application No:</span>
                <span className="font-mono font-semibold text-slate-800">{successData.tnea_application_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Primary Email:</span>
                <span className="font-mono text-slate-800">{successData.email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-bold text-emerald-600">ACTIVATED</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-all shadow-md shadow-blue-500/20"
            >
              <span>Proceed to Sign In</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start space-x-2 text-rose-700 text-xs">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleActivate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Single-Use Activation Token
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="e.g. ACT-XYZ2026004-..."
                    className="block w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600 bg-white font-mono placeholder-slate-400"
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Generated during TNEA allotment import or provided via official SMS/Email dispatch.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Create Secure Password
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
                    placeholder="At least 6 characters"
                    className="block w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600 bg-white placeholder-slate-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Confirm Password
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="block w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600 bg-white placeholder-slate-400"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-600 shadow-md shadow-emerald-600/20 disabled:opacity-50 transition-all"
              >
                {loading ? (
                  <span className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Validating &amp; Activating...</span>
                  </span>
                ) : (
                  <>
                    <span>Activate Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-5 text-center">
              <Link to="/login" className="text-xs font-medium text-blue-600 hover:text-blue-700">
                Already activated? Sign in to your portal &rarr;
              </Link>
            </div>

            {/* Quick Demo Helper */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center">
                <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-500" />
                Demo Seed Token Shortcut
              </p>
              <button
                type="button"
                onClick={() => handleQuickToken('ACT-XYZ2026004-DEMO2026')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-emerald-50 border border-slate-200/80 hover:border-emerald-300 text-xs transition-colors flex items-center justify-between"
              >
                <div>
                  <span className="font-semibold text-slate-800">Candidate: Divya Bharathi K</span>
                  <p className="text-[10px] text-slate-500 font-mono">XYZ2026004 &bull; ACTIVATION PENDING</p>
                </div>
                <span className="text-[10px] font-semibold text-emerald-600 bg-white px-2 py-0.5 rounded border border-emerald-200">
                  Use Token
                </span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
