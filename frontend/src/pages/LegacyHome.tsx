import { Link } from 'react-router-dom'
import {
  FileTextOutlined,
  DollarOutlined,
  ContactsOutlined,
  WarningOutlined,
  SearchOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { Button, Input } from 'antd'

export default function LegacyHome() {
  return (
    <section className="hero">
      <div className="container">
        <h1>Tra cứu thông tin</h1>
        <form className="search" action="/procedures">
          <Input
            size="large"
            placeholder="Nhập từ khóa: thủ tục, mức phạt, đơn vị..."
            prefix={<SearchOutlined />}
            style={{ borderRadius: '999px', flex: 1 }}
          />
          <Button
            type="primary"
            size="large"
            htmlType="submit"
            icon={<SearchOutlined />}
            style={{ borderRadius: '999px' }}
          >
            Tìm
          </Button>
        </form>

        <div className="grid grid-4" style={{ marginTop: 32 }}>
          <Link className="card card-purple" to="/procedures">
            <div className="card-icon">
              <FileTextOutlined />
            </div>
            <h3>Thủ tục</h3>
            <p>Điều kiện, hồ sơ, lệ phí, thời hạn, nơi nộp</p>
          </Link>
          <Link className="card card-blue" to="/fines">
            <div className="card-icon">
              <DollarOutlined />
            </div>
            <h3>Mức phạt</h3>
            <p>Tra cứu theo hành vi, điều/khoản, biện pháp</p>
          </Link>
          <Link className="card card-blue" to="/directory">
            <div className="card-icon">
              <ContactsOutlined />
            </div>
            <h3>Danh bạ</h3>
            <p>Địa chỉ, giờ làm việc, điện thoại, chỉ đường</p>
          </Link>
          <Link className="card card-blue" to="/advisories">
            <div className="card-icon">
              <WarningOutlined />
            </div>
            <h3>Cảnh báo</h3>
            <p>Thủ đoạn lừa đảo mới, nguồn chính thống</p>
          </Link>
        </div>

        <div style={{ marginTop: 32, textAlign: 'center' }}>
          <Link
            to="/chat"
            className="card card-green"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 12,
              padding: '20px 32px',
              textDecoration: 'none',
            }}
          >
            <div className="card-icon" style={{ width: 48, height: 48 }}>
              <MessageOutlined />
            </div>
            <div style={{ textAlign: 'left' }}>
              <h3 style={{ margin: 0, fontSize: 20 }}>Chatbot Tư vấn</h3>
              <p style={{ margin: '4px 0 0', fontSize: 14, opacity: 0.8 }}>
                Hỏi đáp thông tin tự nhiên bằng ngôn ngữ tiếng Việt
              </p>
            </div>
          </Link>
        </div>
      </div>
    </section>
  )
}

