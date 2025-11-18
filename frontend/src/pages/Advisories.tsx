import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdvisories } from '../api'
import { WarningOutlined, HomeOutlined } from '@ant-design/icons'
import { Card, Empty, Spin } from 'antd'

type Advisory = { id:number; title:string; summary:string; source_url?:string }

export default function Advisories(){
  const [items,setItems] = useState<Advisory[]>([])
  const [loading,setLoading] = useState(true)
  useEffect(()=>{ 
    fetchAdvisories()
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false))
  },[])
  return (
    <>
      <nav className="nav">
        <div className="container">
          <Link to="/" style={{display: 'flex', alignItems: 'center', gap: 8, color: 'inherit', textDecoration: 'none'}}>
            <HomeOutlined /> <span>Trang chủ</span>
          </Link>
        </div>
      </nav>
      <div className="container" style={{paddingTop: 32, paddingBottom: 64}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24}}>
          <div className="card-icon" style={{background: 'linear-gradient(135deg,#0B6BD3 0%,#3B82F6 100%)', color: '#fff'}}>
            <WarningOutlined />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: 32, fontWeight: 700}}>Cảnh báo an ninh</h1>
            <p style={{margin: '4px 0 0', color: 'var(--color-muted)'}}>Thủ đoạn lừa đảo mới, nguồn chính thống</p>
          </div>
        </div>
        {loading ? (
          <div style={{textAlign: 'center', padding: 64}}>
            <Spin size="large" />
          </div>
        ) : items.length === 0 ? (
          <Empty description="Chưa có cảnh báo nào" />
        ) : (
          <div className="grid grid-3">
            {items.map(a=>(
              <Card key={a.id} hoverable style={{height: '100%'}}>
                <div style={{display: 'flex', alignItems: 'start', gap: 12, marginBottom: 12}}>
                  <WarningOutlined style={{color: '#ff4d4f', fontSize: 20, marginTop: 2}} />
                  <h3 style={{margin: 0, fontSize: 18, fontWeight: 600, flex: 1}}>{a.title}</h3>
                </div>
                <p style={{margin: 0, color: 'var(--color-muted)', lineHeight: 1.6}}>{a.summary}</p>
                {a.source_url && (
                  <a href={a.source_url} target="_blank" rel="noopener noreferrer" style={{display: 'inline-block', marginTop: 12, fontSize: 14, color: 'var(--color-primary)'}}>
                    Xem nguồn →
                  </a>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

