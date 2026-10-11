import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  Clock,
  Search,
  AlertTriangle,
  UserCheck,
  QrCode,
  ArrowRight,
  Filter,
  RefreshCw,
  MapPin,
  Building,
} from 'lucide-react';
import { PhysicalVerificationService } from '../services/physicalVerification';
import { PhysicalVerificationAppointment, CheckInResult } from '../types';

export const AdminPhysicalVerificationDesk: React.FC = () => {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState<PhysicalVerificationAppointment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Check-in state
  const [checkinInput, setCheckinInput] = useState<string>('');
  const [counterDesk, setCounterDesk] = useState<string>('Verification Desk 1');
  const [checkinResult, setCheckinResult] = useState<CheckInResult | null>(null);
  const [checkinError, setCheckinError] = useState<string | null>(null);
  const [checkingIn, setCheckingIn] = useState<boolean>(false);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const data = await PhysicalVerificationService.listAppointments({
        appointment_date: selectedDate || undefined,
        status_filter: statusFilter || undefined,
        search_query: searchQuery || undefined,
      });
      setAppointments(data);
    } catch (err: any) {
      console.error('Failed to load physical verification appointments', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [selectedDate, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAppointments();
  };

  const handleQuickCheckin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkinInput.trim()) return;
    setCheckingIn(true);
    setCheckinError(null);
    setCheckinResult(null);

    try {
      const res = await PhysicalVerificationService.checkIn({
        token_number: checkinInput.toUpperCase().trim(),
        counter_desk: counterDesk,
      });
      setCheckinResult(res);
      setCheckinInput('');
      fetchAppointments();
    } catch (err: any) {
      setCheckinError(err?.response?.data?.detail || 'Failed to check in candidate with provided token.');
    } finally {
      setCheckingIn(false);
    }
  };

  const handleStartSession = async (applicationId: string, appointmentId?: string) => {
    try {
      const session = await PhysicalVerificationService.startSession(applicationId, {
        appointment_id: appointmentId,
        counter_desk: counterDesk,
      });
      navigate(`/admin/physical-verification/${session.id}`);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to start physical verification session');
    }
  };

  const stats = {
    total: appointments.length,
    scheduled: appointments.filter((a) => a.appointment_status === 'SCHEDULED' || a.appointment_status === 'CONFIRMED').length,
    checkedIn: appointments.filter((a) => a.appointment_status === 'CHECKED_IN').length,
    inProgress: appointments.filter((a) => a.appointment_status === 'IN_PROGRESS').length,
    completed: appointments.filter((a) => a.appointment_status === 'COMPLETED').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Physical Verification Desk</h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 border border-blue-200">
              Phase 5 On-Site Scrutiny
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            XYZ Engineering College — AY 2026–27 Central Admission Verification Counter
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={counterDesk}
            onChange={(e) => setCounterDesk(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white font-medium text-gray-700 shadow-sm focus:ring-2 focus:ring-blue-500"
          >
            <option value="Verification Desk 1">Verification Desk 1</option>
            <option value="Verification Desk 2">Verification Desk 2</option>
            <option value="Verification Desk 3">Verification Desk 3</option>
            <option value="Verification Desk 4">Verification Desk 4</option>
            <option value="Special Quota Counter">Special Quota Counter</option>
          </select>
          <button
            onClick={fetchAppointments}
            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 transition"
            title="Refresh Queue"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Quick Check-In & Scanner Simulator Card */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 text-blue-300 text-xs font-bold uppercase tracking-wider mb-2">
              <QrCode className="h-4 w-4" />
              On-Site Check-In Scanner
            </div>
            <h2 className="text-xl font-bold text-white">Candidate Desk Check-In</h2>
            <p className="text-blue-200 text-sm mt-1">
              Enter candidate Token Number (e.g. <code>PV-20260924-001</code>) or scan their digital appointment QR code.
            </p>
          </div>

          <form onSubmit={handleQuickCheckin} className="flex-1 max-w-lg">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Enter Token (e.g. PV-2026...)"
                  value={checkinInput}
                  onChange={(e) => setCheckinInput(e.target.value)}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-blue-300/70 focus:outline-none focus:ring-2 focus:ring-blue-400 font-mono uppercase text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={checkingIn || !checkinInput.trim()}
                className="px-6 py-3 bg-blue-500 hover:bg-blue-400 text-white font-semibold rounded-xl transition flex items-center gap-2 disabled:opacity-50 shadow-md"
              >
                {checkingIn ? 'Checking In...' : 'Check In'}
                <UserCheck className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>

        {checkinResult && (
          <div className="mt-4 p-4 bg-green-500/20 border border-green-400/30 rounded-xl text-green-100 flex items-center justify-between">
            <div>
              <p className="font-semibold text-white">{checkinResult.message}</p>
              <p className="text-xs text-green-200 mt-0.5">
                Token: <span className="font-mono">{checkinResult.token_number}</span> | Branch:{' '}
                {checkinResult.allotted_branch || 'Allotted'}
              </p>
            </div>
            <button
              onClick={() => handleStartSession(checkinResult.application_id, checkinResult.appointment_id)}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition shadow"
            >
              Start Verification
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {checkinError && (
          <div className="mt-4 p-4 bg-red-500/20 border border-red-400/30 rounded-xl text-red-200 text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {checkinError}
          </div>
        )}
      </div>

      {/* Queue Stat Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-medium text-gray-500">Total Today</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-medium text-amber-600">Scheduled / Confirmed</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{stats.scheduled}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-medium text-blue-600">Checked In (Waiting)</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{stats.checkedIn}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-medium text-purple-600">In Verification</p>
          <p className="text-2xl font-bold text-purple-600 mt-1">{stats.inProgress}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-medium text-green-600">Completed</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{stats.completed}</p>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-600 font-medium">
            <Calendar className="h-4 w-4 text-gray-400" />
            Date:
          </div>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500"
          />

          <div className="flex items-center gap-2 text-sm text-gray-600 font-medium ml-2">
            <Filter className="h-4 w-4 text-gray-400" />
            Status:
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="CHECKED_IN">Checked In</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search token, candidate, app #"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition"
          >
            Search
          </button>
        </form>
      </div>

      {/* Appointments List */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-gray-500 text-sm">Loading appointment queue...</div>
        ) : appointments.length === 0 ? (
          <div className="py-12 text-center text-gray-500 text-sm">
            No physical verification appointments found for the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Token #</th>
                  <th className="px-6 py-3">Slot Time</th>
                  <th className="px-6 py-3">Application / Candidate</th>
                  <th className="px-6 py-3">Counter Desk</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 text-sm">
                {appointments.map((apt) => (
                  <tr key={apt.id} className="hover:bg-gray-50/80 transition">
                    <td className="px-6 py-4 font-mono font-bold text-blue-600">
                      {apt.token_number}
                    </td>
                    <td className="px-6 py-4 text-gray-700">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-gray-400" />
                        <span>
                          {apt.start_time} – {apt.end_time}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">{apt.appointment_date}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">
                        {apt.application_id}
                      </div>
                      <div className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                        <Building className="h-3 w-3" />
                        {apt.location}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-gray-100 text-xs text-gray-700">
                        <MapPin className="h-3 w-3 text-gray-400" />
                        {apt.counter_desk || 'Unassigned'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          apt.appointment_status === 'COMPLETED'
                            ? 'bg-green-100 text-green-800'
                            : apt.appointment_status === 'IN_PROGRESS'
                            ? 'bg-purple-100 text-purple-800'
                            : apt.appointment_status === 'CHECKED_IN'
                            ? 'bg-blue-100 text-blue-800 animate-pulse'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {apt.appointment_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => handleStartSession(apt.application_id, apt.id)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition inline-flex items-center gap-1 shadow-sm"
                      >
                        Open Workspace
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
