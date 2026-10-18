import React, {
  useEffect,
  useRef,
  useState,
  useImperativeHandle,
  forwardRef,
  useCallback,
} from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { PageNav } from './PageNav';
import { Dropzone } from './Dropzone';
import { Loader2, Quote } from 'lucide-react';
import type { Citation, PageData } from '../../types/triage';

try {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
  ).toString();
} catch {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;
}

export interface ViewerHandle {
  scrollToPage: (pageNumber: number, quote?: string) => void;
  resetZoom: () => void;
  fitToWidth: () => void;
}

interface ViewerProps {
  file: File | null;
  pages?: PageData[];
  activeCitation?: Citation | null;
  onFileSelect: (file: File) => void;
  onPageChange?: (page: number) => void;
  isUploading?: boolean;
  uploadError?: string | null;
}

export const Viewer = forwardRef<ViewerHandle, ViewerProps>(
  (
    {
      file,
      pages,
      activeCitation,
      onFileSelect,
      onPageChange,
      isUploading = false,
      uploadError,
    },
    ref
  ) => {
    const [numPages, setNumPages] = useState<number>(1);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [zoom, setZoom] = useState<number>(1.0);
    const [isLoadingDoc, setIsLoadingDoc] = useState<boolean>(false);
    const [docError, setDocError] = useState<string | null>(null);
    const [pdfDocument, setPdfDocument] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
    const [highlightPage, setHighlightPage] = useState<number | null>(null);
    const [highlightQuote, setHighlightQuote] = useState<string | null>(null);
    const [rawTextPages, setRawTextPages] = useState<string[] | null>(null);

    const containerRef = useRef<HTMLDivElement>(null);
    const canvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());
    const renderTasksRef = useRef<Map<number, pdfjsLib.RenderTask>>(new Map());

    useImperativeHandle(ref, () => ({
      scrollToPage(pageNumber: number, quote?: string) {
        if (pageNumber >= 1 && pageNumber <= numPages) {
          setCurrentPage(pageNumber);
          setHighlightPage(pageNumber);
          if (quote) setHighlightQuote(quote);

          setTimeout(() => {
            const el = document.getElementById(`document-page-${pageNumber}`);
            if (el && containerRef.current) {
              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          }, 50);

          setTimeout(() => {
            setHighlightPage(null);
          }, 3500);
        }
      },
      resetZoom() {
        setZoom(1.0);
      },
      fitToWidth() {
        if (containerRef.current) {
          const w = containerRef.current.clientWidth - 48;
          setZoom(Math.min(2.0, Math.max(0.6, w / 620)));
        }
      },
    }));

    useEffect(() => {
      if (activeCitation) {
        const p = activeCitation.page;
        if (p >= 1 && p <= numPages) {
          setCurrentPage(p);
          setHighlightPage(p);
          setHighlightQuote(activeCitation.quote);

          const el = document.getElementById(`document-page-${p}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }

          const timer = setTimeout(() => {
            setHighlightPage(null);
          }, 3500);
          return () => clearTimeout(timer);
        }
      }
    }, [activeCitation, numPages]);

    // Load PDF or TXT
    useEffect(() => {
      if (!file) {
        setPdfDocument(null);
        setRawTextPages(null);
        setNumPages(1);
        setCurrentPage(1);
        setDocError(null);
        return;
      }

      const isTextFile = file.name.toLowerCase().endsWith('.txt');

      if (isTextFile) {
        setIsLoadingDoc(true);
        const reader = new FileReader();
        reader.onload = (e) => {
          const text = (e.target?.result as string) || '';
          const lines = text.split('\n');
          const chunkSize = 50;
          const chunks: string[] = [];
          for (let i = 0; i < lines.length; i += chunkSize) {
            chunks.push(lines.slice(i, i + chunkSize).join('\n'));
          }
          const total = Math.max(1, chunks.length);
          setRawTextPages(chunks);
          setNumPages(total);
          setCurrentPage(1);
          setIsLoadingDoc(false);
        };
        reader.onerror = () => {
          setDocError('Failed to read file contents.');
          setIsLoadingDoc(false);
        };
        reader.readAsText(file);
      } else {
        setIsLoadingDoc(true);
        setDocError(null);

        const fileReader = new FileReader();
        fileReader.onload = async function () {
          try {
            const typedarray = new Uint8Array(this.result as ArrayBuffer);
            const loadingTask = pdfjsLib.getDocument({
              data: typedarray,
              cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@legacy/cmaps/',
              cMapPacked: true,
            });

            const pdf = await loadingTask.promise;
            setPdfDocument(pdf);
            setNumPages(pdf.numPages);
            setCurrentPage(1);
            setIsLoadingDoc(false);
          } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Invalid PDF';
            setDocError(`Unable to render PDF: ${msg}`);
            setIsLoadingDoc(false);
          }
        };
        fileReader.readAsArrayBuffer(file);
      }
    }, [file]);

    // Render PDF page to canvas
    const renderPage = useCallback(
      async (pageNumber: number, canvas: HTMLCanvasElement) => {
        if (!pdfDocument) return;

        if (renderTasksRef.current.has(pageNumber)) {
          try {
            renderTasksRef.current.get(pageNumber)?.cancel();
          } catch {
            // Already cancelled
          }
          renderTasksRef.current.delete(pageNumber);
        }

        try {
          const page = await pdfDocument.getPage(pageNumber);
          const viewport = page.getViewport({ scale: zoom * 1.5 });

          const context = canvas.getContext('2d');
          if (!context) return;

          canvas.height = viewport.height;
          canvas.width = viewport.width;
          canvas.style.width = `${viewport.width / 1.5}px`;
          canvas.style.height = `${viewport.height / 1.5}px`;

          const renderContext = {
            canvasContext: context,
            viewport: viewport,
            canvas: canvas,
          };

          const renderTask = page.render(renderContext);
          renderTasksRef.current.set(pageNumber, renderTask);

          await renderTask.promise;
          renderTasksRef.current.delete(pageNumber);
        } catch (err: unknown) {
          if (err && typeof err === 'object' && 'name' in err && err.name === 'RenderingCancelledException') {
            return;
          }
        }
      },
      [pdfDocument, zoom]
    );

    useEffect(() => {
      if (!pdfDocument) return;
      canvasRefs.current.forEach((canvas, pageNum) => {
        if (canvas) {
          renderPage(pageNum, canvas);
        }
      });
    }, [pdfDocument, zoom, renderPage]);

    const handlePageChange = (newPage: number) => {
      setCurrentPage(newPage);
      onPageChange?.(newPage);
      const el = document.getElementById(`document-page-${newPage}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    if (!file) {
      return (
        <Dropzone
          onFileSelect={onFileSelect}
          isUploading={isUploading}
          uploadError={uploadError}
        />
      );
    }

    const isCurrentPageOcr = Boolean(
      pages?.find((p) => p.page_number === currentPage)?.ocr_applied
    );

    return (
      <div className="h-full w-full flex flex-col bg-[#0c0e12] overflow-hidden select-none">
        <PageNav
          filename={file.name}
          currentPage={currentPage}
          totalPages={numPages}
          zoom={zoom}
          isCurrentPageOcr={isCurrentPageOcr}
          onPageChange={handlePageChange}
          onZoomChange={(newZoom) => setZoom(newZoom)}
          onFitWidth={() => {
            if (containerRef.current) {
              const w = containerRef.current.clientWidth - 48;
              setZoom(Math.max(0.6, Math.min(2.0, w / 620)));
            }
          }}
          onResetZoom={() => setZoom(1.0)}
          onNewUpload={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.txt';
            input.onchange = (e) => {
              const files = (e.target as HTMLInputElement).files;
              if (files && files[0]) onFileSelect(files[0]);
            };
            input.click();
          }}
        />

        {isLoadingDoc && (
          <div className="flex-1 flex items-center justify-center gap-2 text-slate-500 text-xs font-mono">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
            <span>Rendering document streams...</span>
          </div>
        )}

        {docError && (
          <div className="p-3 m-3 text-xs text-rose-400 border border-[#1e232d] bg-[#11141a]">
            {docError}
          </div>
        )}

        {!isLoadingDoc && !docError && (
          <div
            ref={containerRef}
            className="flex-1 overflow-y-auto overflow-x-auto p-4 flex flex-col items-center gap-4 bg-[#0c0e12]"
          >
            {/* PDF Canvas Pages */}
            {pdfDocument &&
              Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => {
                const isHighlighted = highlightPage === pageNum;
                const pageOcr = pages?.find((p) => p.page_number === pageNum)?.ocr_applied;

                return (
                  <div
                    key={`page-${pageNum}`}
                    id={`document-page-${pageNum}`}
                    className={`relative rounded border transition-all ${
                      isHighlighted
                        ? 'border-[#d4a359] shadow-[0_0_15px_rgba(212,163,89,0.2)]'
                        : 'border-[#1e232d]'
                    }`}
                  >
                    {/* Page Marker Tag */}
                    <div className="absolute top-1 left-2 z-10 flex items-center gap-1.5">
                      <span className="text-[10px] font-mono text-slate-400 bg-[#11141a]/90 px-1.5 py-0.5 rounded border border-[#1e232d]">
                        p. {pageNum}
                      </span>
                      {pageOcr && (
                        <span className="text-[9px] font-mono text-[#d4a359] bg-[#11141a]/90 px-1 py-0.5 rounded border border-[#d4a359]/30">
                          OCR
                        </span>
                      )}
                    </div>

                    {/* Active Citation Quote Highlight Banner */}
                    {isHighlighted && highlightQuote && (
                      <div className="absolute -top-7 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#161a22] border border-[#d4a359] text-[10px] font-mono text-[#d4a359] shadow-lg">
                        <Quote className="w-3 h-3" />
                        <span>Citation Reference (Page {pageNum})</span>
                      </div>
                    )}

                    <div className="bg-white rounded overflow-hidden">
                      <canvas
                        ref={(el) => {
                          if (el) {
                            canvasRefs.current.set(pageNum, el);
                            renderPage(pageNum, el);
                          } else {
                            canvasRefs.current.delete(pageNum);
                          }
                        }}
                        className="block"
                      />
                    </div>
                  </div>
                );
              })}

            {/* Plain Text Pages */}
            {rawTextPages &&
              rawTextPages.map((pageText, pageIdx) => {
                const pageNum = pageIdx + 1;
                const isHighlighted = highlightPage === pageNum;

                return (
                  <div
                    key={`txt-page-${pageNum}`}
                    id={`document-page-${pageNum}`}
                    style={{
                      width: `${Math.round(600 * zoom)}px`,
                      minHeight: `${Math.round(780 * zoom)}px`,
                    }}
                    className={`relative p-6 rounded bg-[#11141a] text-slate-300 font-mono text-xs leading-relaxed selectable-text border transition-all ${
                      isHighlighted
                        ? 'border-[#d4a359] bg-[#d4a359]/5'
                        : 'border-[#1e232d]'
                    }`}
                  >
                    <div className="text-[10px] text-slate-500 mb-3 border-b border-[#1e232d] pb-1 flex justify-between">
                      <span>p. {pageNum} of {numPages}</span>
                    </div>

                    {isHighlighted && highlightQuote && (
                      <div className="mb-3 p-2 rounded bg-[#d4a359]/10 border border-[#d4a359]/30 text-[#d4a359] text-[11px]">
                        "{highlightQuote}"
                      </div>
                    )}

                    <pre className="whitespace-pre-wrap font-mono text-[11px] leading-5 text-slate-300">
                      {pageText}
                    </pre>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    );
  }
);

Viewer.displayName = 'Viewer';
