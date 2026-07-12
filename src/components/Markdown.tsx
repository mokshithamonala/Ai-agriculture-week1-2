import React from 'react';

interface MarkdownProps {
  text: string;
}

export default function Markdown({ text }: MarkdownProps) {
  if (!text) return null;

  // Split content into lines
  const lines = text.split('\n');

  // Simple helper to parse and render bold text inline
  const renderInlineStyles = (txt: string) => {
    // Regex matches double asterisks **text**
    const parts = txt.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-extrabold text-primary dark:text-emerald-400">
            {part.slice(2, -2)}
          </strong>
        );
      }
      // Parse single asterisks *text*
      const subParts = part.split(/(\*.*?\*)/g);
      return subParts.map((subPart, j) => {
        if (subPart.startsWith('*') && subPart.endsWith('*')) {
          return (
            <em key={`${i}-${j}`} className="font-semibold italic">
              {subPart.slice(1, -1)}
            </em>
          );
        }
        return subPart;
      });
    });
  };

  return (
    <div className="space-y-1.5 text-base font-semibold leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();

        // 1. Headings
        if (trimmed.startsWith('### ')) {
          return (
            <h3 key={idx} className="text-lg font-extrabold mt-3 mb-1 text-primary dark:text-emerald-400">
              {renderInlineStyles(trimmed.substring(4))}
            </h3>
          );
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h2 key={idx} className="text-xl font-extrabold mt-4 mb-2 text-primary dark:text-emerald-400 border-b border-border/20 pb-0.5">
              {renderInlineStyles(trimmed.substring(3))}
            </h2>
          );
        }
        if (trimmed.startsWith('# ')) {
          return (
            <h1 key={idx} className="text-2xl font-black mt-5 mb-3 text-primary dark:text-emerald-400">
              {renderInlineStyles(trimmed.substring(2))}
            </h1>
          );
        }

        // 2. Unordered Bullet Lists
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
          return (
            <div key={idx} className="flex items-start space-x-2 pl-2">
              <span className="text-primary dark:text-emerald-400 font-bold mt-1 text-xs">•</span>
              <span className="flex-1">{renderInlineStyles(trimmed.substring(2))}</span>
            </div>
          );
        }

        // 3. Ordered Numbered Lists
        const numberedMatch = trimmed.match(/^(\d+)\.\s(.*)/);
        if (numberedMatch) {
          return (
            <div key={idx} className="flex items-start space-x-2 pl-2">
              <span className="text-primary dark:text-emerald-400 font-bold">{numberedMatch[1]}.</span>
              <span className="flex-1">{renderInlineStyles(numberedMatch[2])}</span>
            </div>
          );
        }

        // 4. Empty Line
        if (trimmed === '') {
          return <div key={idx} className="h-1.5" />;
        }

        // 5. Plain Paragraph
        return <p key={idx}>{renderInlineStyles(line)}</p>;
      })}
    </div>
  );
}
