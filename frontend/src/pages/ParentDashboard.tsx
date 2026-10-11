import React, { useState, useEffect } from 'react';
import {
  Shield,
  KeyRound,
  AlertCircle,
} from 'lucide-react';
import { onboardingService } from '../services/onboarding';
import {
  OnboardingProfile,
  GuidanceCard,
} from '../types';

export const ParentDashboard: React.FC = () => {
  const [linkedStudent, setLinkedStudent] = useState<Record<string, any> | null>(null);
  const [profile, setProfile] = useState<OnboardingProfile | null>(null);
  const [guidanceCards, setGuidanceCards] = useState<GuidanceCard[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Redemption state
  const [inviteToken, setInviteToken] = useState('');
  const [parentName, setParentName] = useState('');
  const [parentPhone, setParentPhone] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [redeemLoading, setRedeemLoading] = useState(false);
  const [redeemSuccess, setRedeemSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadParentPortal();
  }, []);

  const loadParentPortal = async () => {
    try {
      setLoading(true);
      setError(null);

      const stu = await onboardingService.getLinkedStudentSummary();
      setLinkedStudent(stu);

      const [prof, cards] = await Promise.all([
        onboardingService.getLinkedStudentOnboarding(),
        onboardingService.getParentGuidance(),
      ]);

      setProfile(prof);
      setGuidanceCards(cards);
    } catch (err: any) {
      if (err.response?.status === 403 || err.response?.status === 404) {
        setLinkedStudent(null);
      } else {
        setError(err.response?.data?.detail || 'Unable to load parent portal.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRedeemToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteToken.trim() || !parentName.trim() || !parentPhone.trim()) return;

    try {
      setRedeemLoading(true);
      setError(null);
      const res = await onboardingService.redeemParentInvitation({
        invite_token: inviteToken.trim(),
        parent_name: parentName.trim(),
        phone: parentPhone.trim(),
        email: parentEmail.trim() || undefined,
      });

      setRedeemSuccess(res.message);
      setInviteToken('');
      await loadParentPortal();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to redeem invitation token.');
    } finally {
      setRedeemLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium">Loading Parent Portal...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Institutional Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-8 rounded-3xl shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-semibold rounded-full uppercase tracking-wider">
                Prototype / Demo Only
              </span>
              <span className="px-3 py-1 bg-indigo-500/30 border border-indigo-400/40 text-indigo-200 text-xs font-semibold rounded-full">
                Parent & Guardian Portal
              </span>
            </div>
            <h1 className="text-3xl font-black tracking-tight">XYZ Engineering College (Code: XYZ)</h1>
            <p className="text-indigo-200 text-sm mt-1">
              Academic Year 2026–27 • Parent Engagement & Induction Information Desk
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md border border-white/15 px-5 py-3 rounded-xl flex items-center gap-3">
            <Shield className="w-6 h-6 text-emerald-400" />
            <div>
              <p className="text-xs text-indigo-200 font-semibold">Security Boundary</p>
              <p className="text-sm font-bold text-white">Anti-IDOR Protected</p>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Unlinked State: Invitation Token Redemption */}
      {!linkedStudent ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm max-w-xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto">
              <KeyRound className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Link to Your Admitted Student</h2>
            <p className="text-xs text-slate-500">
              Enter the single-use invitation token provided by your student to activate your Parent Portal access.
            </p>
          </div>

          {redeemSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl text-emerald-800 text-xs font-semibold">
              {redeemSuccess}
            </div>
          )}

          <form onSubmit={handleRedeemToken} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Invitation Token *
              </label>
              <input
                type="text"
                required
                value={inviteToken}
                onChange={(e) => setInviteToken(e.target.value)}
                placeholder="Paste token received from student"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Your Full Name *
              </label>
              <input
                type="text"
                required
                value={parentName}
                onChange={(e) => setParentName(e.target.value)}
                placeholder="e.g. S. Ramanathan"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Mobile Number *
              </label>
              <input
                type="text"
                required
                value={parentPhone}
                onChange={(e) => setParentPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={parentEmail}
                onChange={(e) => setParentEmail(e.target.value)}
                placeholder="parent@example.com"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={redeemLoading}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition flex items-center justify-center gap-2"
            >
              {redeemLoading ? 'Verifying Token...' : 'Redeem Token & Link Student'}
            </button>
          </form>
        </div>
      ) : (
        /* Linked State: Student Overview & Guidance */
        <div className="space-y-8">
          {/* Linked Student Card */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded">
                  Linked Ward Profile
                </span>
                <h2 className="text-2xl font-black text-slate-800 mt-2">{linkedStudent.full_name}</h2>
                <p className="text-sm text-slate-500">{linkedStudent.allotted_branch}</p>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Relationship</p>
                  <p className="font-bold text-slate-800">{linkedStudent.relationship}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Admission Status</p>
                  <p className="font-bold text-emerald-600">{linkedStudent.application_status}</p>
                </div>
              </div>
            </div>

            {profile && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <div className="bg-slate-50 p-4 rounded-xl">
                  <p className="text-xs text-slate-500 font-semibold uppercase">Student Type</p>
                  <p className="font-bold text-slate-800">{profile.student_type}</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl">
                  <p className="text-xs text-slate-500 font-semibold uppercase">Onboarding Status</p>
                  <p className="font-bold text-slate-800">{profile.onboarding_status}</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl">
                  <p className="text-xs text-slate-500 font-semibold uppercase">Checklist Completion</p>
                  <p className="font-bold text-indigo-600">{profile.overall_completion_percentage}%</p>
                </div>
              </div>
            )}
          </div>

          {/* Guidance Cards */}
          <div className="space-y-4">
            <h3 className="text-xl font-black text-slate-800">Parent Guidance & Directory</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {guidanceCards.map((card, idx) => (
                <div key={idx} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md">
                      {card.category}
                    </span>
                    <span className="text-xs text-slate-400">Ref: {card.source_reference}</span>
                  </div>
                  <h4 className="font-bold text-slate-800 text-base">{card.title}</h4>

                  <div className="text-xs text-slate-600 space-y-2 pt-1">
                    {Object.entries(card.data).map(([k, v]) => (
                      <div key={k} className="flex flex-col">
                        <span className="font-semibold text-slate-700 capitalize">{k.replace(/_/g, ' ')}:</span>
                        <span className="text-slate-600">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
