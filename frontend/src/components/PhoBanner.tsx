import { useNavigate } from 'react-router-dom'
import './PhoBanner.css'

export default function PhoBanner() {
  const navigate = useNavigate()

  const handleAiClick = () => {
    navigate('/legacy-home')
  }

  return (
    <div className="pho-page">
      <header className="header-banner">
        <div className="overlay-blur" />
        <div className="header-left" aria-hidden="true">
          <div className="logo">
            <div className="logo-inner" />
          </div>
          <div className="header-text">
            <div className="org-name">CÔNG AN THÀNH PHỐ Huế</div>
            <div className="dept-name">PHÒNG THANH TRA</div>
            <div className="slogan">Vì bình yên cố đô- Vì nhân dân phục vụ</div>
          </div>
        </div>

        <div className="logo-container">
          <div className="logo-emblem">
            <img src="/logochuan.png" alt="Huy hiệu Công an nhân dân" loading="lazy" />
          </div>
        </div>

        <div className="text-container">
          <div className="header-text header-text-visible">
            <div className="org-name">CÔNG AN THÀNH PHỐ HUẾ</div>
            <div className="dept-name">PHÒNG THANH TRA</div>
            <div className="slogan">Vì bình yên của cố đô - Vì nhân dân phục vụ</div>
          </div>
        </div>
      </header>

      <main className="main-container">
        <button className="ai-staff-button" type="button" onClick={handleAiClick}>
          NHÂN VIÊN AI
        </button>

        <h1 className="main-title">PHÒNG THANH TRA</h1>
        <p className="description">
          Cẩm nang các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên
        </p>

        <div className="bottom-section">
          <div className="qr-section">
            <div className="qr-container">
              <div className="qr-code" />
            </div>
            <p className="qr-label">PHIÊN BẢN THỬ NGHIỆM</p>
          </div>

          <div className="officer-section">
            <img src="/chiensi.png" alt="Nhân viên" className="officer-image" loading="lazy" />
          </div>
        </div>
      </main>
    </div>
  )
}

