import React from 'react';
import { Sparkles, ArrowUpRight } from 'lucide-react';

interface QuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PRACTICAL_PROMPTS = [
  'What is the notice period for termination?',
  'Identify uncapped liability or indemnity clauses',
  'Are there automatic renewal terms?',
];

export const QuickPrompts: React.FC<QuickPromptsProps> = ({
  onSelectPrompt,
  disabled = false,
}) => {
  return (
    <div className="p-4 space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
        <span>Suggested Contract Queries</span>
      </div>

      <div className="space-y-1.5">
        {PRACTICAL_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelectPrompt(prompt)}
            className="w-full text-left p-2.5 rounded bg-[#161a22] hover:bg-[#1c212c] border border-[#1e232d] hover:border-slate-500 text-xs text-slate-300 hover:text-slate-100 transition-colors flex items-center justify-between group disabled:opacity-50 cursor-pointer"
          >
            <span>{prompt}</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 transition-transform shrink-0 ml-2" />
          </button>
        ))}
      </div>
    </div>
  );
};
