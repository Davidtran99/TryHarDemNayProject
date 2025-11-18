import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchOffices } from '../api'
import { ContactsOutlined, SearchOutlined, HomeOutlined, EnvironmentOutlined, ClockCircleOutlined, PhoneOutlined } from '@ant-design/icons'
import { Button, Input, Card, Tag, Empty } from 'antd'

type Office = { id:number; unit_name:string; address?:string; district?:string; phone?:string; working_hours?:string; email?:string }

export default function Directory(){
  const [items,setItems] = useState<Office[]>([])
  const [q,setQ] = useState('')
  const [loading,setLoading] = useState(false)
  const load = async (params:any={}) => {
    setLoading(true)
    try {
      setItems(await fetchOffices(params))
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
            <ContactsOutlined />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: 32, fontWeight: 700}}>Danh bạ điểm tiếp dân</h1>
            <p style={{margin: '4px 0 0', color: 'var(--color-muted)'}}>Địa chỉ, giờ làm việc, điện thoại, chỉ đường</p>
          </div>
        </div>
        <Card style={{marginBottom: 24}}>
          <form onSubmit={(e)=>{e.preventDefault(); load({ q })}} style={{display: 'flex', gap: 12}}>
            <Input 
              size="large"
              placeholder="Tìm theo tên đơn vị hoặc địa chỉ..." 
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
          <Empty description="Không tìm thấy đơn vị nào" />
        ) : (
          <div className="grid grid-3">
            {items.map(o=>(
              <Card key={o.id} hoverable style={{height: '100%'}}>
                <h3 style={{marginTop: 0, fontSize: 18, fontWeight: 600}}>{o.unit_name}</h3>
                {o.district && <Tag color="blue" style={{marginBottom: 12}}>{o.district}</Tag>}
                <div style={{marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14, color: 'var(--color-muted)'}}>
                  {o.address && (
                    <div style={{display: 'flex', alignItems: 'start', gap: 8}}>
                      <EnvironmentOutlined style={{marginTop: 2}} />
                      <span>{o.address}</span>
                    </div>
                  )}
                  {o.working_hours && (
                    <div style={{display: 'flex', alignItems: 'start', gap: 8}}>
                      <ClockCircleOutlined style={{marginTop: 2}} />
                      <span>{o.working_hours}</span>
                    </div>
                  )}
                  {o.phone && (
                    <div style={{display: 'flex', alignItems: 'start', gap: 8}}>
                      <PhoneOutlined style={{marginTop: 2}} />
                      <span>{o.phone}</span>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

