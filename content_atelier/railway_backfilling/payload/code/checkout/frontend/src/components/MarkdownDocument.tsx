import React from 'react';

type Block =
  | { type: 'h1' | 'h2' | 'h3' | 'p'; text: string }
  | { type: 'quote'; lines: string[] }
  | { type: 'ul' | 'ol'; items: string[] }
  | { type: 'hr' };

function isStructural(line: string): boolean {
  return (
    line.startsWith('# ') ||
    line.startsWith('## ') ||
    line.startsWith('### ') ||
    line.startsWith('> ') ||
    line.startsWith('- ') ||
    line.startsWith('* ') ||
    /^\d+\.\s/.test(line) ||
    line.trim() === '---'
  );
}

function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (line.trim() === '') {
      index += 1;
      continue;
    }
    if (line.trim() === '---') {
      blocks.push({ type: 'hr' });
      index += 1;
      continue;
    }
    if (line.startsWith('### ')) {
      blocks.push({ type: 'h3', text: line.slice(4) });
      index += 1;
      continue;
    }
    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', text: line.slice(3) });
      index += 1;
      continue;
    }
    if (line.startsWith('# ')) {
      blocks.push({ type: 'h1', text: line.slice(2) });
      index += 1;
      continue;
    }
    if (line.startsWith('> ')) {
      const quote: string[] = [];
      while (index < lines.length && lines[index].startsWith('> ')) {
        quote.push(lines[index].slice(2));
        index += 1;
      }
      blocks.push({ type: 'quote', lines: quote });
      continue;
    }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const items: string[] = [];
      while (index < lines.length && (lines[index].startsWith('- ') || lines[index].startsWith('* '))) {
        items.push(lines[index].slice(2));
        index += 1;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s/.test(lines[index])) {
        items.push(lines[index].replace(/^\d+\.\s/, ''));
        index += 1;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }

    const paragraph = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() !== '' && !isStructural(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push({ type: 'p', text: paragraph.join(' ') });
  }

  return blocks;
}

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const pattern = /(\[[^\]]+\]\(https?:\/\/[^)\s]+\)|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let token = 0;

  while ((match = pattern.exec(text))) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index));
    const value = match[0];
    const link = /^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(value);
    if (link) {
      nodes.push(<a key={`${keyPrefix}-a-${token}`} href={link[2]} target="_blank" rel="noopener noreferrer" className="text-[#5070FF] underline underline-offset-2">{link[1]}</a>);
    } else if (value.startsWith('**')) {
      nodes.push(
        <strong key={`${keyPrefix}-b-${token}`} className="font-semibold text-[#221E17]">
          {value.slice(2, -2)}
        </strong>
      );
    } else {
      nodes.push(
        <em key={`${keyPrefix}-i-${token}`} className="italic">
          {value.slice(1, -1)}
        </em>
      );
    }
    cursor = match.index + value.length;
    token += 1;
  }

  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

interface MarkdownDocumentProps {
  markdown: string;
}

export const MarkdownDocument: React.FC<MarkdownDocumentProps> = ({ markdown }) => {
  const blocks = parseMarkdown(markdown);

  return (
    <article className="space-y-4 text-sm leading-relaxed text-[#221E17]">
      {blocks.map((block, index) => {
        const key = `md-${index}`;
        if (block.type === 'h1') {
          return (
            <h3 key={key} className="font-editorial text-2xl font-bold tracking-tight text-[#221E17]">
              {renderInline(block.text, key)}
            </h3>
          );
        }
        if (block.type === 'h2') {
          return (
            <h4
              key={key}
              className="font-editorial text-lg font-bold text-[#221E17] pt-2 border-t border-[#E0DFE2]"
            >
              {renderInline(block.text, key)}
            </h4>
          );
        }
        if (block.type === 'h3') {
          return (
            <h5 key={key} className="text-xs font-mono uppercase tracking-wider text-[#5070FF] font-semibold">
              {renderInline(block.text, key)}
            </h5>
          );
        }
        if (block.type === 'quote') {
          return (
            <blockquote
              key={key}
              className="border-l-2 border-[#5070FF] bg-[#FAF9F7] px-4 py-3 rounded-r-xl text-[#4B4137] italic"
            >
              {block.lines.map((line, lineIndex) => (
                <p key={`${key}-q-${lineIndex}`}>{renderInline(line, `${key}-q-${lineIndex}`)}</p>
              ))}
            </blockquote>
          );
        }
        if (block.type === 'ul' || block.type === 'ol') {
          const List = block.type === 'ul' ? 'ul' : 'ol';
          return (
            <List
              key={key}
              className={`space-y-1.5 pl-5 text-[#4B4137] ${
                block.type === 'ul' ? 'list-disc' : 'list-decimal'
              }`}
            >
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-i-${itemIndex}`}>{renderInline(item, `${key}-i-${itemIndex}`)}</li>
              ))}
            </List>
          );
        }
        if (block.type === 'hr') {
          return <hr key={key} className="border-[#E0DFE2]" />;
        }
        if (block.type === 'p') {
          return (
            <p key={key} className="text-[#4B4137]">
              {renderInline(block.text, key)}
            </p>
          );
        }
        return null;
      })}
    </article>
  );
};
