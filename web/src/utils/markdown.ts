import hljs from 'highlight.js'
import { marked } from 'marked'
import 'highlight.js/styles/github-dark.css'

marked.setOptions({
  gfm: true,
  breaks: true,
  async: false,
})

marked.use({
  renderer: {
    code({ text, lang }: { text: string; lang?: string }): string {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted = hljs.highlight(text, { language }).value
      return `<pre class="hljs"><code class="language-${language}">${highlighted}</code></pre>`
    },
  },
})

export function renderMarkdown(content: string): string {
  if (!content) return ''
  return marked.parse(content) as string
}
