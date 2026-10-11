import React, { useState } from 'react';
import { 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Circle, 
  ChevronDown, 
  ChevronUp, 
  Sparkles, 
  User, 
  Cpu
} from 'lucide-react';
import { StudentJourneyTimeline as JourneyType } from '../types';

interface Props {
  journey: JourneyType | null;
}

export const StudentJourneyTimeline: React.FC<Props> = ({ journey }) => {
  const [showAllEvents, setShowAllEvents] = useState(false);

  if (!journey) return null;

  const stageDefs = [
    { key: 'allotment', label: '1. Allotment', desc: 'TNEA Seat Allotted' },
    { key: 'activation', label: '2. Activation', desc: 'Portal Account Active' },
    { key: 'application', label: '3. Application', desc: 'Form & Declarations' },
    { key: 'documents', label: '4. Documents', desc: 'Certificates Uploaded' },
    { key: 'digital_scrutiny', label: '5. Scrutiny', desc: 'Desk Verification' },
    { key: 'physical_verification', label: '6. Physical Verification', desc: 'Originals Check' },
    { key: 'payment', label: '7. Payment', desc: 'DD / Online Settlement' },
    { key: 'erp', label: '8. ERP Staging', desc: 'Institutional Sync' },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="flex items-center space-x-1 text-[10px] font-bold text-emerald-700 bg-emerald-100/90 px-2 py-0.5 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            <span>COMPLETED</span>
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span className="flex items-center space-x-1 text-[10px] font-bold text-blue-700 bg-blue-100/90 px-2 py-0.5 rounded-full animate-pulse">
            <Clock className="w-3 h-3" />
            <span>IN PROGRESS</span>
          </span>
        );
      case 'ACTION_REQUIRED':
        return (
          <span className="flex items-center space-x-1 text-[10px] font-bold text-amber-800 bg-amber-200 px-2 py-0.5 rounded-full">
            <AlertCircle className="w-3 h-3" />
            <span>ACTION REQUIRED</span>
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="flex items-center space-x-1 text-[10px] font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">
            <AlertCircle className="w-3 h-3" />
            <span>BLOCKED</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
            <Circle className="w-2.5 h-2.5" />
            <span>NOT STARTED</span>
          </span>
        );
    }
  };

  const displayedEvents = showAllEvents ? journey.events : journey.events.slice(0, 5);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center">
              <Sparkles className="w-4 h-4 mr-2 text-indigo-600" />
              Unified Admission Journey
            </h3>
            <span className="text-[10px] font-mono bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded border border-indigo-200">
              8 AUTHORITATIVE DOMAIN STAGES
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time multi-stage lifecycle progression for App #{journey.application_number}
          </p>
        </div>
      </div>

      {/* 8-Stage Progression Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {stageDefs.map(s => {
          const stageStatus = (journey.stages as any)?.[s.key] || 'NOT_STARTED';
          const isDone = stageStatus === 'COMPLETED';
          const isCurrent = stageStatus === 'IN_PROGRESS' || stageStatus === 'ACTION_REQUIRED';

          return (
            <div
              key={s.key}
              className={`p-3 rounded-xl border transition-all flex flex-col justify-between ${
                isDone
                  ? 'bg-emerald-50/50 border-emerald-200'
                  : isCurrent
                  ? 'bg-blue-50/70 border-blue-300 ring-2 ring-blue-500/20 shadow-sm'
                  : 'bg-slate-50/60 border-slate-200 opacity-80'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold text-slate-900 leading-tight truncate">
                    {s.label}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 leading-snug mb-2">{s.desc}</p>
              </div>
              <div className="mt-auto">{getStatusBadge(stageStatus)}</div>
            </div>
          );
        })}
      </div>

      {/* Unified Event Audit Log */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Operational Audit Trail ({journey.events.length} Events)
          </span>
          {journey.events.length > 5 && (
            <button
              onClick={() => setShowAllEvents(!showAllEvents)}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center space-x-1"
            >
              <span>{showAllEvents ? 'Show Less' : `View All (${journey.events.length})`}</span>
              {showAllEvents ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <div className="space-y-2.5">
          {displayedEvents.length === 0 ? (
            <p className="text-xs text-slate-400 italic py-2">No timeline events recorded yet.</p>
          ) : (
            displayedEvents.map(ev => {
              const isHuman = ev.actor_type === 'HUMAN_ACTION';
              return (
                <div
                  key={ev.id}
                  className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-start space-x-3 text-xs hover:bg-slate-50/90 transition-colors"
                >
                  <div className="mt-0.5 flex-shrink-0">
                    {isHuman ? (
                      <div className="w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                        <User className="w-3.5 h-3.5" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center font-bold">
                        <Cpu className="w-3.5 h-3.5" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900">{ev.title}</span>
                        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
                          isHuman ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-200 text-slate-700'
                        }`}>
                          {ev.actor_type}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500 font-medium">
                          &bull; {ev.stage}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">
                        {new Date(ev.timestamp).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    <p className="text-slate-600 mt-1">{ev.description}</p>

                    <div className="flex items-center space-x-3 mt-1.5 text-[10px] text-slate-400 font-mono">
                      <span>Actor: <strong className="text-slate-700">{ev.actor_name}</strong> ({ev.actor_role})</span>
                      {ev.reference_id && (
                        <span>Ref: <strong className="text-slate-700">{ev.reference_id}</strong></span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
