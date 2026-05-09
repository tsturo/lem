import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

const MARKDOWN_CSS = `
.lem-md > p:first-of-type {
  font-size: 17px;
  line-height: 1.6;
  max-width: 640px;
  color: var(--t-text-2);
}
.lem-md ul {
  list-style: none;
  padding-left: 20px;
  margin: 8px 0;
}
.lem-md ul li {
  position: relative;
  margin-bottom: 6px;
  padding-left: 4px;
}
.lem-md ul li::before {
  content: '';
  position: absolute;
  left: -14px;
  top: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6c5ce7, #00cec9);
}
.lem-md blockquote {
  border-left: 4px solid var(--t-teal, #00cec9);
  background: rgba(0, 206, 201, 0.05);
  margin: 14px 0;
  padding: 12px 16px;
  border-radius: 0 8px 8px 0;
}
.lem-md blockquote p {
  margin: 0;
}
.lem-md pre {
  font-family: var(--t-font-mono, 'SF Mono', Menlo, Consolas, monospace);
  background: var(--t-surface, #f7f7fb);
  padding: 14px 18px;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}
.lem-md code:not(pre code) {
  font-family: var(--t-font-mono, 'SF Mono', Menlo, Consolas, monospace);
  background: var(--t-surface, #f7f7fb);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 0.88em;
}
`

const ACCENT_STYLE: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6c5ce7, #00cec9)',
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  color: 'transparent',
}

const H1_STYLE: React.CSSProperties = {
  fontFamily: 'var(--t-font)',
  fontWeight: 700,
  fontSize: 30,
  letterSpacing: '-0.02em',
  lineHeight: 1.2,
  color: 'var(--t-text)',
  marginTop: 24,
  marginBottom: 12,
}

const H2_STYLE: React.CSSProperties = {
  fontFamily: 'var(--t-font)',
  fontWeight: 700,
  fontSize: 22,
  letterSpacing: '-0.01em',
  lineHeight: 1.2,
  color: 'var(--t-text)',
  marginTop: 20,
  marginBottom: 8,
}

const H3_STYLE: React.CSSProperties = {
  fontFamily: 'var(--t-font)',
  fontWeight: 500,
  fontSize: 17,
  lineHeight: 1.2,
  color: 'var(--t-text)',
  marginTop: 16,
  marginBottom: 6,
}

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (node !== null && typeof node === 'object' && 'props' in node) {
    const el = node as { props: { children?: React.ReactNode } }
    return extractText(el.props.children)
  }
  return ''
}

function H1WithAccent({ children }: { children?: React.ReactNode }) {
  const text = extractText(children)
  const words = text.split(' ')
  const lastWord = words.pop() ?? ''
  const rest = words.join(' ')

  return (
    <h1 data-lem-h1 style={H1_STYLE}>
      {rest ? `${rest} ` : ''}
      <span data-accent style={ACCENT_STYLE}>{lastWord}</span>
    </h1>
  )
}

const COMPONENTS: Components = {
  h1(props) {
    return <H1WithAccent>{props.children}</H1WithAccent>
  },
  h2(props) {
    return <h2 data-lem-h2 style={H2_STYLE}>{props.children}</h2>
  },
  h3(props) {
    return <h3 data-lem-h3 style={H3_STYLE}>{props.children}</h3>
  },
  blockquote(props) {
    return <blockquote data-lem-blockquote>{props.children}</blockquote>
  },
}

export function MarkdownBody({ content }: { content: string }) {
  return (
    <div
      data-markdown-body
      className="lem-md"
      style={{
        maxWidth: 720,
        fontFamily: 'var(--t-font)',
        fontSize: 15,
        lineHeight: 1.6,
        color: 'var(--t-text)',
      }}
    >
      <style>{MARKDOWN_CSS}</style>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
