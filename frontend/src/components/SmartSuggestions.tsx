import React from 'react'
import { Tag, Button } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'

type SmartSuggestionsProps = {
  suggestions: string[]
  onSuggestionClick: (suggestion: string) => void
  intent?: string
}

export default function SmartSuggestions({ suggestions, onSuggestionClick, intent }: SmartSuggestionsProps) {
  if (!suggestions || suggestions.length === 0) {
    return null
  }

  return (
    <div style={{
      marginTop: 12,
      padding: 12,
      background: '#f9f9f9',
      borderRadius: 8,
      border: '1px solid #e0e0e0'
    }}>
      <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 12, color: 'var(--color-muted)'}}>
        <ThunderboltOutlined style={{color: '#faad14'}} />
        <span style={{fontWeight: 600, color: 'var(--color-text)'}}>Gợi ý câu hỏi tiếp theo</span>
      </div>
      <div style={{display: 'flex', flexWrap: 'wrap', gap: 8}}>
        {suggestions.map((suggestion, idx) => (
          <Button
            key={idx}
            size="small"
            type="text"
            onClick={() => onSuggestionClick(suggestion)}
            style={{
              fontSize: 12,
              padding: '4px 8px',
              height: 'auto',
              border: '1px solid #d9d9d9',
              borderRadius: 4,
            }}
          >
            {suggestion}
          </Button>
        ))}
      </div>
    </div>
  )
}

