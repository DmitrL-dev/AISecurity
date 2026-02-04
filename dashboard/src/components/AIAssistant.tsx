'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { useAnalyze } from '@/lib/hooks'

interface Message {
  id: number
  type: 'user' | 'assistant'
  content: string
  timestamp: string
  isTyping?: boolean
}

// Simple markdown-like rendering
function renderContent(content: string) {
  // Bold: **text**
  let html = content.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
  // Code: `code`
  html = html.replace(/`(.+?)`/g, '<code class="px-1 py-0.5 bg-[#111827] rounded text-cyan-400 text-xs">$1</code>')
  // Links: [text](url)
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-purple-400 underline hover:text-purple-300" target="_blank">$1</a>')
  // Newlines
  html = html.replace(/\n/g, '<br/>')
  
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

const initialMessages: Message[] = [
  {
    id: 1,
    type: 'assistant',
    content: "👋 Hello! I'm your **AI Security Assistant**. Ask me about threats, payloads, or security recommendations.",
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  },
  {
    id: 2,
    type: 'assistant',
    content: '⚠️ **Recommendation:** Based on recent payload analysis, we recommend enabling enhanced DLP for all `Regie.ai` interactions to prevent sensitive data exfiltration.\n\nReview policy rules for "Secrets and Credentials".',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
]

// Typing indicator component
function TypingIndicator() {
  return (
    <div className="flex gap-2">
      <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
        <Bot className="w-3 h-3 text-purple-400" />
      </div>
      <div className="bg-[#242938] p-3 rounded-lg flex items-center gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}

export function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { analyze, analyzing } = useAnalyze()

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = async () => {
    if (!input.trim() || analyzing) return
    
    const userMessage: Message = {
      id: messages.length + 1,
      type: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    setMessages(prev => [...prev, userMessage])
    const query = input
    setInput('')
    setIsTyping(true)
    
    try {
      // Check if it looks like a prompt to analyze (contains attack patterns)
      const isAnalyzeRequest = /ignore|forget|pretend|jailbreak|injection|attack|test prompt/i.test(query)
      
      if (isAnalyzeRequest) {
        // Use BRAIN for threat analysis
        const result = await analyze({ prompt: query })
        
        let response = ''
        if (result.is_safe) {
          response = `✅ **Analysis Complete**\n\nThe prompt appears to be **safe**.\n\n- Risk Score: \`${(result.risk_score * 100).toFixed(1)}%\`\n- Processing Time: \`${result.processing_time_ms}ms\``
        } else {
          const threatEmoji = '\u{1F6A8}'
          const detectionList = result.detections?.map((d: { threat_type: string; engine: string; details: string }) => `\u2022 **${d.threat_type}** (${d.engine}): ${d.details}`).join('\n') || ''
          response = `${threatEmoji} **Threat Detected!**\n\n- Risk Score: \`${(result.risk_score * 100).toFixed(1)}%\`\n- Detections: ${result.detections?.length || 0}\n\n${detectionList}`
        }
        
        setIsTyping(false)
        setMessages(prev => [...prev, {
          id: prev.length + 1,
          type: 'assistant',
          content: response,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }])
      } else {
        // Use DeepSeek AI for general questions
        const res = await fetch('/api/assistant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query })
        })
        
        if (res.ok) {
          const data = await res.json()
          setIsTyping(false)
          setMessages(prev => [...prev, {
            id: prev.length + 1,
            type: 'assistant',
            content: data.message,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }])
        } else {
          throw new Error('AI API failed')
        }
      }
    } catch (_error) {
      setIsTyping(false)
      setMessages(prev => [...prev, {
        id: prev.length + 1,
        type: 'assistant',
        content: `I'm analyzing your query: "${query}"\n\n💡 **Tip:** You can test prompts for injection attacks, ask about specific threat types, or request security recommendations.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    }
  }

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] flex flex-col h-[350px]">
      {/* Header */}
      <div className="p-4 border-b border-[#374151]">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bot className="w-5 h-5 text-purple-400" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full" />
          </div>
          <h3 className="font-semibold">AI Security Assistant</h3>
        </div>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-2 ${msg.type === 'user' ? 'justify-end' : ''}`}>
            {msg.type === 'assistant' && (
              <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <Bot className="w-3 h-3 text-purple-400" />
              </div>
            )}
            <div className={`
              max-w-[80%] p-3 rounded-lg text-sm leading-relaxed
              ${msg.type === 'user' 
                ? 'bg-purple-500 text-white' 
                : 'bg-[#242938] text-gray-300'
              }
            `}>
              {renderContent(msg.content)}
            </div>
            {msg.type === 'user' && (
              <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-3 h-3 text-cyan-400" />
              </div>
            )}
          </div>
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <div className="p-4 border-t border-[#374151]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type your question here..."
            disabled={analyzing}
            className="flex-1 px-3 py-2 bg-[#111827] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none text-sm disabled:opacity-50"
          />
          <button 
            onClick={handleSend}
            disabled={analyzing || !input.trim()}
            className="p-2 bg-purple-500 rounded-lg hover:bg-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}
