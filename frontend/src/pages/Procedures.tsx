import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProcedures } from '../api'
import { FileTextOutlined, SearchOutlined, HomeOutlined } from '@ant-design/icons'
import { Button, Input, Card, Tag, Empty } from 'antd'

type Procedure = { id:number; title:string; domain:string; level?:string; conditions?:string }

export default function Procedures(){
  const [items,setItems] = useState<Procedure[]>([])
  const [q,setQ] = useState('')
  const [loading,setLoading] = useState(false)
  const load = async (params:any={}) => {
    setLoading(true)
    try {
      const data = await fetchProcedures(params)
      setItems(data)
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
          <div className="card-icon" style={{background: 'linear-gradient(135deg,#8B5CF6 0%,#A78BFA 100%)', color: '#fff'}}>
            <FileTextOutlined />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: 32, fontWeight: 700}}>Thủ tục hành chính</h1>
            <p style={{margin: '4px 0 0', color: 'var(--color-muted)'}}>Tra cứu điều kiện, hồ sơ, lệ phí, thời hạn</p>
          </div>
        </div>
        <Card style={{marginBottom: 24}}>
          <form onSubmit={(e)=>{e.preventDefault(); load({ q })}} style={{display: 'flex', gap: 12}}>
            <Input 
              size="large"
              placeholder="Từ khóa: cư trú, ANTT, PCCC..." 
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
          <Empty description="Không tìm thấy thủ tục nào" />
        ) : (
          <div className="grid grid-3">
            {items.map(p=>(
              <Card key={p.id} hoverable style={{height: '100%'}}>
                <h3 style={{marginTop: 0, fontSize: 18, fontWeight: 600}}>{p.title}</h3>
                <div style={{marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap'}}>
                  <Tag color="purple">{p.domain}</Tag>
                  {p.level && <Tag>{p.level}</Tag>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

