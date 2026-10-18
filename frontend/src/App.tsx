import React, { useRef, useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { Shell } from './components/layout/Shell';
import { Viewer, ViewerHandle } from './components/document/Viewer';
import { QueryBox } from './components/triage/QueryBox';
import { QuickPrompts } from './components/triage/QuickPrompts';
import { ResultView } from './components/triage/ResultView';
import { useDocument } from './hooks/useDocument';
import { useTriageQuery } from './hooks/useTriageQuery';
import { usePdfNavigation } from './hooks/usePdfNavigation';
import { checkBackendPing } from './api/documents';
import type { Citation } from './types/triage';
import { Loader2 } from 'lucide-react';

export function App() {
  const {
    file,
    ingestData,
    isUploading,
    uploadError,
    handleFileSelect,
  } = useDocument();

  const {
    isLoading: isQuerying,
    error: queryError,
    activeQuery,
    activeResponse,
    submitQuery,
    resetQuery,
  } = useTriageQuery();

  const {
    activeCitation,
    jumpToCitation,
    jumpToPage,
  } = usePdfNavigation();

  const [queryInputText, setQueryInputText] = useState<string>('');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);

  const viewerRef = useRef<ViewerHandle>(null);

  // Monitor backend round-trip latency
  useEffect(() => {
    let isMounted = true;
    const ping = async () => {
      const res = await checkBackendPing();
      if (isMounted) {
        setIsBackendOnline(res.ok);
        setLatencyMs(res.ok ? res.latencyMs : null);
      }
    };

    ping();
    const interval = setInterval(ping, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleCitationClick = (citation: Citation) => {
    jumpToCitation(citation);
    viewerRef.current?.scrollToPage(citation.page, citation.quote);
  };

  const handleQuerySubmit = async (queryToRun: string) => {
    if (!ingestData?.document_id) return;
    await submitQuery(ingestData.document_id, queryToRun);
  };

  const handleDocumentChange = async (selectedFile: File) => {
    resetQuery();
    setQueryInputText('');
    await handleFileSelect(selectedFile);
  };

  const handleOpenFileDialog = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.txt';
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files[0]) {
        handleDocumentChange(files[0]);
      }
    };
    input.click();
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0c0e12] text-slate-200 font-sans">
      <Header
        documentName={ingestData?.filename}
        totalPages={ingestData?.total_pages}
        latencyMs={latencyMs}
        isBackendOnline={isBackendOnline}
        onOpenDocument={handleOpenFileDialog}
      />

      <Shell
        defaultLeftPercent={58}
        leftPanel={
          <Viewer
            ref={viewerRef}
            file={file}
            pages={ingestData?.pages}
            activeCitation={activeCitation}
            onFileSelect={handleDocumentChange}
            onPageChange={jumpToPage}
            isUploading={isUploading}
            uploadError={uploadError}
          />
        }
        rightPanel={
          <div className="h-full flex flex-col bg-[#11141a] overflow-hidden">
            <QueryBox
              value={queryInputText}
              onChange={setQueryInputText}
              onSubmit={handleQuerySubmit}
              isLoading={isQuerying}
              disabled={!file}
            />

            <div className="flex-1 overflow-y-auto">
              {/* No file loaded */}
              {!file && (
                <div className="h-full flex items-center justify-center p-6 text-slate-500 text-xs font-mono select-none">
                  Open a document to inspect clauses and run queries.
                </div>
              )}

              {/* Document loaded, idle */}
              {file && !isQuerying && !activeResponse && !queryError && (
                <div className="space-y-4">
                  <QuickPrompts
                    onSelectPrompt={(prompt) => {
                      setQueryInputText(prompt);
                      handleQuerySubmit(prompt);
                    }}
                  />

                  <div className="px-4 py-2 text-[11px] font-mono text-slate-500 border-t border-[#1e232d]">
                    {ingestData?.total_pages} pages parsed & indexed into local memory.
                  </div>
                </div>
              )}

              {/* Query Running */}
              {isQuerying && (
                <div className="h-full flex items-center justify-center p-6 text-slate-400 text-xs font-mono gap-2 select-none">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#d4a359]" />
                  <span>Searching clauses...</span>
                </div>
              )}

              {/* Query Error */}
              {queryError && (
                <div className="m-3 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono rounded">
                  {queryError}
                </div>
              )}

              {/* Active Result View */}
              {activeResponse && !isQuerying && (
                <ResultView
                  question={activeQuery || ''}
                  response={activeResponse}
                  activeCitation={activeCitation}
                  onCitationClick={handleCitationClick}
                />
              )}
            </div>
          </div>
        }
      />
    </div>
  );
}

export default App;
