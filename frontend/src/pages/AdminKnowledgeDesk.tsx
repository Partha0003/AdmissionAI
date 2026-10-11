import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  CheckCircle,
  Archive,
  Layers,
  RefreshCw,
  Search,
  Check,
  AlertCircle,
  Clock,
  X,
} from 'lucide-react';
import { chatService } from '../services/chat';
import {
  KnowledgeDocument,
  KnowledgeCategory,
  KnowledgeLifecycleState,
} from '../types';

export const AdminKnowledgeDesk: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Ingestion Modal
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [ingestTitle, setIngestTitle] = useState('');
  const [ingestCategory, setIngestCategory] = useState<KnowledgeCategory>('GENERAL');
  const [ingestDescription, setIngestDescription] = useState('');
  const [ingestContent, setIngestContent] = useState('');
  const [ingestAutoActivate, setIngestAutoActivate] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Document details modal
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await chatService.listKnowledgeDocuments(
        selectedCategory === 'ALL' ? undefined : selectedCategory
      );
      setDocuments(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load knowledge documents.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateVersion = async (versionId: string) => {
    try {
      await chatService.activateKnowledgeVersion(versionId);
      setSuccessMessage('Version successfully activated for RAG retrieval.');
      await loadDocuments();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to activate knowledge version.');
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestTitle.trim() || !ingestContent.trim()) {
      setError('Title and Content are required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await chatService.ingestKnowledge({
        title: ingestTitle.trim(),
        category: ingestCategory,
        description: ingestDescription.trim() || undefined,
        content: ingestContent.trim(),
        auto_activate: ingestAutoActivate,
      });

      setShowIngestModal(false);
      setIngestTitle('');
      setIngestDescription('');
      setIngestContent('');
      setSuccessMessage('Knowledge document successfully ingested and chunked.');
      await loadDocuments();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to ingest knowledge document.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const categories: { label: string; value: string }[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Admission Guidelines', value: 'ADMISSION_GUIDELINES' },
    { label: 'Document Checklist', value: 'DOCUMENT_VERIFICATION' },
    { label: 'Physical Verification', value: 'PHYSICAL_VERIFICATION' },
    { label: 'Fee & Payment', value: 'FEE_AND_PAYMENT' },
    { label: 'FAQ', value: 'FAQ' },
    { label: 'General Policy', value: 'GENERAL' },
  ];

  const getLifecycleBadge = (state: KnowledgeLifecycleState) => {
    switch (state) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            ACTIVE
          </span>
        );
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            READY
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <RefreshCw className="w-3.5 h-3.5 text-amber-600 animate-spin" />
            PROCESSING
          </span>
        );
      case 'ARCHIVED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            <Archive className="w-3.5 h-3.5 text-slate-500" />
            ARCHIVED
          </span>
        );
      case 'DRAFT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            DRAFT
          </span>
        );
      default:
        return null;
    }
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesCategory =
      selectedCategory === 'ALL' || doc.category === selectedCategory;
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.description || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 text-white rounded-2xl p-6 shadow-lg border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-bold tracking-wider uppercase bg-blue-500/30 text-blue-200 rounded-md border border-blue-400/30">
                Phase 9 • Administration
              </span>
              <span className="px-2.5 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 rounded-md border border-emerald-400/30">
                Authoritative Knowledge Store
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">
              Admission AI Knowledge Base & Policy Desk
            </h1>
            <p className="text-sm text-slate-300 mt-1">
              XYZ Engineering College (Code: XYZ) • Strict Lifecycle: DRAFT → READY → ACTIVE → ARCHIVED
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowIngestModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Ingest Document / Policy
            </button>
          </div>
        </div>
      </div>

      {/* Notifications / Alerts */}
      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-medium flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition shrink-0 ${
                selectedCategory === cat.value
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Documents Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200 space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
          <div className="text-xs">Loading authoritative knowledge base...</div>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200 space-y-2">
          <BookOpen className="w-8 h-8 text-slate-400 mx-auto" />
          <div className="text-sm font-semibold text-slate-700">
            No knowledge documents found
          </div>
          <div className="text-xs text-slate-400">
            {searchQuery
              ? 'Try adjusting your search criteria.'
              : 'Ingest institutional admission policies or checklists.'}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocs.map((doc) => {
            const activeVersion = (doc.versions || []).find(
              (v) => v.lifecycle_state === 'ACTIVE'
            );
            const readyVersion = (doc.versions || []).find(
              (v) => v.lifecycle_state === 'READY'
            );
            const totalVersions = (doc.versions || []).length;

            return (
              <div
                key={doc.id}
                className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between hover:border-blue-300 transition"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-semibold rounded-md uppercase">
                      {doc.category.replace('_', ' ')}
                    </span>
                    {activeVersion && getLifecycleBadge(activeVersion.lifecycle_state)}
                  </div>

                  <h3 className="font-bold text-slate-900 text-sm mb-1 leading-snug">
                    {doc.title}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-4">
                    {doc.description || (activeVersion ? activeVersion.content.slice(0, 120) + '...' : 'No description.')}
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span className="flex items-center gap-1 text-[11px]">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      {totalVersions} {totalVersions === 1 ? 'Version' : 'Versions'}
                    </span>
                    {activeVersion && (
                      <span className="text-[11px] font-mono text-slate-500">
                        Active: v{activeVersion.version_number}
                      </span>
                    )}
                  </div>

                  {/* Ready version activation notice */}
                  {readyVersion && (
                    <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-center justify-between gap-2">
                      <div>
                        <span className="font-semibold block">v{readyVersion.version_number} Ready</span>
                        <span className="text-[10px] text-blue-700">Awaiting activation</span>
                      </div>
                      <button
                        onClick={() => handleActivateVersion(readyVersion.id)}
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-md shadow-xs transition"
                      >
                        Activate
                      </button>
                    </div>
                  )}

                  <button
                    onClick={() => setSelectedDoc(doc)}
                    className="w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold text-xs rounded-lg border border-slate-200 transition text-center"
                  >
                    Inspect Versions & Chunks
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Ingest Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-800 text-base">
                  Ingest Policy or Knowledge Document
                </h3>
              </div>
              <button
                onClick={() => setShowIngestModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleIngest} className="flex-1 overflow-y-auto space-y-4 pr-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Document Title *
                </label>
                <input
                  type="text"
                  required
                  value={ingestTitle}
                  onChange={(e) => setIngestTitle(e.target.value)}
                  placeholder="e.g., Hostels & Residential Rules 2026–27"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Category *
                  </label>
                  <select
                    value={ingestCategory}
                    onChange={(e) => setIngestCategory(e.target.value as KnowledgeCategory)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="ADMISSION_GUIDELINES">ADMISSION GUIDELINES</option>
                    <option value="DOCUMENT_VERIFICATION">DOCUMENT VERIFICATION</option>
                    <option value="PHYSICAL_VERIFICATION">PHYSICAL VERIFICATION</option>
                    <option value="FEE_AND_PAYMENT">FEE & PAYMENT</option>
                    <option value="FAQ">FAQ</option>
                    <option value="GENERAL">GENERAL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Short Description
                  </label>
                  <input
                    type="text"
                    value={ingestDescription}
                    onChange={(e) => setIngestDescription(e.target.value)}
                    placeholder="Brief description of policy"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Markdown Content * (Sections split automatically)
                </label>
                <textarea
                  required
                  rows={8}
                  value={ingestContent}
                  onChange={(e) => setIngestContent(e.target.value)}
                  placeholder="# Section 1: Policy Overview&#10;XYZ Engineering College rules for..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="auto_activate"
                  checked={ingestAutoActivate}
                  onChange={(e) => setIngestAutoActivate(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                />
                <label htmlFor="auto_activate" className="text-xs font-medium text-slate-700">
                  Immediately activate this version (archives previous active version)
                </label>
              </div>

              <div className="pt-4 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm"
                >
                  {isSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Ingest & Process
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document Inspector Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-3xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-semibold rounded uppercase">
                  {selectedDoc.category}
                </span>
                <h3 className="font-bold text-slate-900 text-base mt-1">
                  {selectedDoc.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Document Version History
              </h4>

              <div className="space-y-3">
                {(selectedDoc.versions || []).map((ver) => (
                  <div
                    key={ver.id}
                    className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800">
                          Version {ver.version_number}
                        </span>
                        {getLifecycleBadge(ver.lifecycle_state)}
                      </div>
                      {ver.lifecycle_state === 'READY' && (
                        <button
                          onClick={() => handleActivateVersion(ver.id)}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded text-xs shadow-xs"
                        >
                          Activate
                        </button>
                      )}
                    </div>

                    <div className="text-[11px] text-slate-500 font-mono">
                      Hash: {ver.content_hash.slice(0, 16)}... | Created:{' '}
                      {new Date(ver.created_at).toLocaleString()}
                    </div>

                    <div className="mt-2 p-3 bg-white border border-slate-200 rounded-lg font-mono text-[11px] text-slate-700 max-h-32 overflow-y-auto whitespace-pre-wrap">
                      {ver.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedDoc(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
