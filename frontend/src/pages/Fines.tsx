import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchFines } from '../api'
import { DollarOutlined, SearchOutlined, HomeOutlined } from '@ant-design/icons'
import { Button, Input, Card, Tag, Empty } from 'antd'

type Fine = { id:number; code:string; name:string; decree?:string; article?:string; min_fine?:number; max_fine?:number }

export default function Fines(){
  const [items,setItems] = useState<Fine[]>([])
  const [q,setQ] = useState('')
  const [loading,setLoading] = useState(false)
  const load = async (params:any={}) => {
    setLoading(true)
    try {
      setItems(await fetchFines(params))
    } catch(e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }
  useEffect(()=>{ load({ q }) },[])
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
            <DollarOutlined />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: 32, fontWeight: 700}}>Mức phạt giao thông</h1>
            <p style={{margin: '4px 0 0', color: 'var(--color-muted)'}}>Tra cứu theo hành vi, điều/khoản, biện pháp</p>
          </div>
        </div>
        <Card style={{marginBottom: 24}}>
          <form onSubmit={(e)=>{e.preventDefault(); load({ q })}} style={{display: 'flex', gap: 12}}>
            <Input 
              size="large"
              placeholder="Nhập hành vi: vượt đèn đỏ, nồng độ cồn..." 
              value={q} 
              onChange={e=>setQ(e.target.value)}
              prefix={<SearchOutlined />}
              style={{flex: 1}}
            />
            <Button type="primary" size="large" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              Tìm
            </Button>
          </form>
        </Card>
        {items.length === 0 && !loading ? (
          <Empty description="Không tìm thấy mức phạt nào" />
        ) : (
          <div className="grid grid-3">
            {items.map(f=>(
              <Card key={f.id} hoverable style={{height: '100%'}}>
                <h3 style={{marginTop: 0, fontSize: 18, fontWeight: 600}}>{f.name}</h3>
                <div style={{marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap'}}>
                  <Tag color="blue">{f.code}</Tag>
                  {f.decree && <Tag>{f.decree}</Tag>}
                  {f.article && <Tag>{f.article}</Tag>}
                </div>
                {(f.min_fine || f.max_fine) && (
                  <p style={{marginTop: 12, marginBottom: 0, color: 'var(--color-muted)', fontSize: 14}}>
                    {f.min_fine && f.max_fine ? `${f.min_fine.toLocaleString('vi-VN')} - ${f.max_fine.toLocaleString('vi-VN')} VNĐ` : 
                     f.min_fine ? `Từ ${f.min_fine.toLocaleString('vi-VN')} VNĐ` : 
                     f.max_fine ? `Đến ${f.max_fine.toLocaleString('vi-VN')} VNĐ` : ''}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

