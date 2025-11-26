import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { chat, resetChatSession } from '../api'
import { MessageOutlined, SendOutlined, HomeOutlined, RobotOutlined, UserOutlined, UploadOutlined } from '@ant-design/icons'
import { Input, Button, Card, Tag, Spin } from 'antd'
import SmartSuggestions from '../components/SmartSuggestions'

type Message = {
  role: 'user' | 'bot'
  content: string
  intent?: string
  results?: any[]
  timestamp: Date
  session_id?: string
  best_match?: number
  relevance_scores?: Array<{ index: number; score: number; is_best_match: boolean }>
}


export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'bot',
      content: 'Xin chào! Tôi có thể giúp bạn tra cứu các thông tin liên quan về các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (messageText?: string, resetSession: boolean = false) => {
    const textToSend = messageText || input.trim()
    if (!textToSend || loading) return

    const userMessage: Message = {
      role: 'user',
      content: textToSend,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await chat(textToSend, sessionId, resetSession)
      
      // Update session_id from response
      if (response.session_id) {
        setSessionId(response.session_id)
      }
      
      const botMessage: Message = {
        role: 'bot',
        content: response.message || 'Xin lỗi, không thể tìm thấy thông tin.',
        intent: response.intent,
        results: response.results || [],
        timestamp: new Date(),
        session_id: response.session_id,
        best_match: response.best_match,
        relevance_scores: response.relevance_scores
      }
      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error(error)
      const errorMessage: Message = {
        role: 'bot',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleResetSession = () => {
    resetChatSession()
    setSessionId(null)
    setMessages([
      {
        role: 'bot',
        content: 'Xin chào! Tôi có thể giúp bạn tra cứu các thông tin liên quan về các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên',
        timestamp: new Date()
      }
    ])
  }

  const getResultLink = (result: any) => {
    if (result.type === 'fine') return `/fines`
    if (result.type === 'procedure') return `/procedures`
    if (result.type === 'office') return `/directory`
    if (result.type === 'advisory') return `/advisories`
    return '/'
  }

  const formatFineAmount = (minFine: number | null, maxFine: number | null, formatted?: string | null): string | null => {
    if (formatted) return formatted
    if (minFine !== null && maxFine !== null) {
      return `${minFine.toLocaleString('vi-VN')} - ${maxFine.toLocaleString('vi-VN')} VNĐ`
    } else if (minFine !== null) {
      return `${minFine.toLocaleString('vi-VN')} VNĐ`
    }
    return null
  }

  const getResultTitle = (result: any) => {
    if (result.type === 'fine') return result.data.name
    if (result.type === 'procedure') return result.data.title
    if (result.type === 'office') return result.data.unit_name
    if (result.type === 'advisory') return result.data.title
    return ''
  }

  const generateFollowUpSuggestions = (intent?: string, results?: any[]): string[] => {
    const suggestions: string[] = []
    
    if (intent === 'search_fine' && results && results.length > 0) {
      suggestions.push('Còn mức phạt nào khác không?')
      suggestions.push('Điều luật liên quan là gì?')
      suggestions.push('Biện pháp khắc phục như thế nào?')
    } else if (intent === 'search_procedure' && results && results.length > 0) {
      suggestions.push('Hồ sơ cần chuẩn bị gì?')
      suggestions.push('Lệ phí là bao nhiêu?')
      suggestions.push('Thời hạn xử lí là bao lâu?')
    } else if (intent === 'search_office' && results && results.length > 0) {
      suggestions.push('Số điện thoại liên hệ?')
      suggestions.push('Giờ làm việc như thế nào?')
      suggestions.push('Địa chỉ cụ thể ở đâu?')
    } else if (intent === 'search_advisory' && results && results.length > 0) {
      suggestions.push('Còn cảnh báo nào khác không?')
      suggestions.push('Cách phòng tránh như thế nào?')
    } else if (intent === 'search_legal' && results && results.length > 0) {
      suggestions.push('Có điều khoản liên quan nào khác không?')
      suggestions.push('Tải file gốc văn bản này?')
      suggestions.push('Tóm tắt nội dung chính của điều này?')
    }
    
    return suggestions.slice(0, 3)
  }


  return (
    <>
      <nav className="nav">
        <div className="container" style={{display: 'flex', gap: 16}}>
          <Link to="/" style={{display: 'flex', alignItems: 'center', gap: 8, color: 'inherit', textDecoration: 'none'}}>
            <HomeOutlined /> <span>Trang chủ</span>
          </Link>
          <Link to="/legal-upload" style={{display: 'flex', alignItems: 'center', gap: 8, color: 'inherit', textDecoration: 'none'}}>
            <UploadOutlined /> <span>Import tài liệu</span>
          </Link>
        </div>
      </nav>
      <div className="container" style={{paddingTop: 32, paddingBottom: 64}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24}}>
          <div className="card-icon" style={{background: 'linear-gradient(135deg,#10B981 0%,#34D399 100%)', color: '#fff'}}>
            <MessageOutlined />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: 32, fontWeight: 700}}>Chatbot Tư vấn</h1>
            <p style={{margin: '4px 0 0', color: 'var(--color-muted)'}}>Hỏi đáp các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên</p>
          </div>
        </div>

        <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>
          {/* Chat Card */}
          <Card style={{minHeight: '500px', display: 'flex', flexDirection: 'column'}}>
            {/* Messages Area */}
            <div style={{
              flex: 1,
              minHeight: '400px',
              maxHeight: '500px',
              overflowY: 'auto',
              padding: '20px',
              marginBottom: 16,
            }}>
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    gap: 12,
                    marginBottom: 20,
                    flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  }}
                >
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: msg.role === 'user' ? 'var(--color-primary)' : '#10B981',
                      color: '#fff',
                      flexShrink: 0,
                    }}
                  >
                    {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  </div>
                  <div style={{flex: 1, maxWidth: '75%'}}>
                    {/* Timestamp and context indicator */}
                    <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 11, color: 'var(--color-muted)'}}>
                      <span>
                        {msg.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {msg.intent && (
                        <Tag size="small" color={
                          msg.intent === 'search_fine' ? 'blue' :
                          msg.intent === 'search_procedure' ? 'purple' :
                          msg.intent === 'search_office' ? 'green' :
                          msg.intent === 'search_advisory' ? 'orange' : 'default'
                        }>
                          {msg.intent.replace('search_', '')}
                        </Tag>
                      )}
                      {idx > 0 && messages[idx - 1].session_id === msg.session_id && (
                        <span style={{fontSize: 10, opacity: 0.7}}>• Context</span>
                      )}
                    </div>
                    <div
                      style={{
                        padding: '12px 16px',
                        borderRadius: 12,
                        background: msg.role === 'user' ? 'var(--color-primary)' : '#f5f5f5',
                        color: msg.role === 'user' ? '#fff' : 'var(--color-text)',
                        marginBottom: 8,
                        lineHeight: 1.6,
                        wordBreak: 'break-word',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {msg.content}
                    </div>
                    {msg.results && msg.results.length > 0 && (
                      <div style={{display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8}}>
                        {msg.results.slice(0, 3).map((result, rIdx) => {
                          const isBestMatch = (msg as any).best_match === rIdx || (msg as any).relevance_scores?.[rIdx]?.is_best_match
                          const fineAmount = result.type === 'fine' 
                            ? formatFineAmount(
                                result.data.min_fine,
                                result.data.max_fine,
                                result.data.fine_amount_formatted
                              )
                            : null
                          const isLegal = result.type === 'legal'
                          const cardStyles = {
                                display: 'block',
                                padding: 12,
                                border: isBestMatch ? '2px solid #faad14' : '1px solid #e0e0e0',
                                borderRadius: 8,
                                textDecoration: 'none',
                            color: 'inherit' as const,
                                transition: 'all 0.2s',
                                background: isBestMatch ? '#fffbf0' : '#fff',
                                boxShadow: isBestMatch ? '0 2px 8px rgba(250, 173, 20, 0.15)' : 'none',
                          }

                          const cardContent = (
                            <>
                              <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4}}>
                                <div style={{fontWeight: 600, fontSize: 15, flex: 1}}>
                                  {isLegal ? `${result.data.section_code || ''} ${result.data.section_title || ''}`.trim() || result.data.document_title : getResultTitle(result)}
                                </div>
                                {isBestMatch && (
                                  <Tag color="gold" style={{margin: 0, fontSize: 11}}>
                                    Kết quả chính xác nhất
                                  </Tag>
                                )}
                              </div>
                              {fineAmount && (
                                <div style={{fontSize: 13, color: '#1890ff', marginBottom: 6, fontWeight: 500}}>
                                  Mức phạt: {fineAmount}
                                </div>
                              )}
                              {isLegal && (
                                <div style={{fontSize: 13, color: '#555', marginBottom: 8, lineHeight: 1.5}}>
                                  <div style={{fontWeight: 500}}>
                                    Thuộc: {result.data.document_title} ({result.data.document_code})
                                  </div>
                                  <div style={{marginTop: 4}}>
                                    {(result.data.excerpt || result.data.content)?.slice(0, 220)}{(result.data.excerpt || result.data.content)?.length > 220 ? '...' : ''}
                                  </div>
                                  {result.data.page_start && (
                                    <div style={{marginTop: 4, fontSize: 12, color: '#8c8c8c'}}>
                                      Trang: {result.data.page_start}{result.data.page_end && result.data.page_end !== result.data.page_start ? `-${result.data.page_end}` : ''}
                                    </div>
                                  )}
                                  <div style={{display: 'flex', gap: 8, marginTop: 8}}>
                                    {result.data.download_url && (
                                      <a href={result.data.download_url} target="_blank" rel="noopener noreferrer" style={{fontSize: 12, color: '#d46b08'}}>
                                        Xem/Tải file gốc
                                      </a>
                                    )}
                                    {result.data.source_url && !result.data.download_url && (
                                      <a href={result.data.source_url} target="_blank" rel="noopener noreferrer" style={{fontSize: 12, color: '#d46b08'}}>
                                        Mở nguồn
                                      </a>
                                    )}
                                  </div>
                                </div>
                              )}
                              <Tag color={
                                result.type === 'fine' ? 'blue' :
                                result.type === 'procedure' ? 'purple' :
                                result.type === 'office' ? 'green' :
                                result.type === 'advisory' ? 'orange' :
                                '#d46b08'
                              } style={{margin: 0}}>
                                {result.type === 'fine' ? 'Mức phạt' :
                                 result.type === 'procedure' ? 'Thủ tục' :
                                 result.type === 'office' ? 'Đơn vị' :
                                 result.type === 'advisory' ? 'Cảnh báo' : 'Tài liệu pháp lý'}
                              </Tag>
                            </>
                          )

                          if (isLegal) {
                            return (
                              <div
                                key={rIdx}
                                style={cardStyles}
                              >
                                {cardContent}
                              </div>
                            )
                          }

                          return (
                            <Link
                              key={rIdx}
                              to={getResultLink(result)}
                              style={cardStyles}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = isBestMatch ? '#faad14' : 'var(--color-primary)'
                                e.currentTarget.style.background = isBestMatch ? '#fffbf0' : '#f9f9f9'
                                e.currentTarget.style.transform = 'translateX(4px)'
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = isBestMatch ? '#faad14' : '#e0e0e0'
                                e.currentTarget.style.background = isBestMatch ? '#fffbf0' : '#fff'
                                e.currentTarget.style.transform = 'translateX(0)'
                              }}
                            >
                              {cardContent}
                            </Link>
                          )
                        })}
                      </div>
                    )}
                    {/* Follow-up suggestions for bot messages */}
                    {msg.role === 'bot' && msg.results && msg.results.length > 0 && (
                      <SmartSuggestions
                        suggestions={generateFollowUpSuggestions(msg.intent, msg.results)}
                        onSuggestionClick={handleSend}
                        intent={msg.intent}
                      />
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div style={{display: 'flex', gap: 12, marginBottom: 20}}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#10B981',
                      color: '#fff',
                      flexShrink: 0,
                    }}
                  >
                    <RobotOutlined />
                  </div>
                  <div style={{flex: 1, display: 'flex', alignItems: 'center', padding: '12px 16px'}}>
                    <Spin size="small" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{
              display: 'flex',
              gap: 12,
              borderTop: '1px solid #e0e0e0',
              paddingTop: 16,
              paddingBottom: 8,
              background: '#fff',
            }}>
              <Input
                size="large"
                placeholder="Nhập câu hỏi của bạn..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onPressEnter={() => handleSend()}
                disabled={loading}
                style={{flex: 1}}
              />
              <Button
                type="primary"
                size="large"
                icon={<SendOutlined />}
                onClick={() => handleSend()}
                loading={loading}
                disabled={!input.trim()}
              >
                Gửi
              </Button>
            </div>
          </Card>

        </div>
      </div>
    </>
  )
}
