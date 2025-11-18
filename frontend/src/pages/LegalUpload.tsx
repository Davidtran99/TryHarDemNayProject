import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, Tag, message, Space } from 'antd'
import { UploadOutlined, HomeOutlined, FileDoneOutlined, FileTextOutlined } from '@ant-design/icons'
import { uploadLegalDocument, fetchIngestionJob, type IngestionJob } from '../api'

export default function LegalUpload() {
  const [messageApi, contextHolder] = message.useMessage()
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [job, setJob] = useState<IngestionJob | null>(null)
  const [result, setResult] = useState<IngestionJob | null>(null)
  const uploadToken = import.meta.env.VITE_LEGAL_UPLOAD_TOKEN

  const generateCodeFromName = (name: string) => {
    const base = name.split('.').slice(0, -1).join('.') || name
    return base
      .replace(/[^a-zA-Z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .toUpperCase() || `DOC-${Date.now()}`
  }

  const pollJob = useCallback(
    async (jobId: string) => {
      try {
        const updated = await fetchIngestionJob(jobId)
        setJob(updated)
        if (updated.status === 'completed') {
          setResult(updated)
          messageApi.success('Import tài liệu hoàn tất')
        } else if (updated.status === 'failed') {
          messageApi.error(updated.error_message || 'Import thất bại')
        }
      } catch (err: any) {
        messageApi.error(err?.message || 'Không thể kiểm tra tiến độ import')
      }
    },
    [messageApi]
  )

  useEffect(() => {
    if (!job) return
    if (job.status === 'completed' || job.status === 'failed') return
    const timer = setTimeout(() => pollJob(job.id), 2000)
    return () => clearTimeout(timer)
  }, [job, pollJob])

  const handleUpload = async () => {
    if (!file) {
      messageApi.error('Vui lòng chọn file PDF hoặc DOCX')
      return
    }

    try {
      setUploading(true)
      const code = generateCodeFromName(file.name)
      const response = await uploadLegalDocument({
        file,
        code,
        title: code.replace(/-/g, ' '),
        docType: 'other',
        mimeType: file.type,
        token: uploadToken,
      })
      setJob(response)
      setResult(response.status === 'completed' ? response : null)
      if (response.status === 'completed') {
        messageApi.success('Import tài liệu hoàn tất')
      } else {
        messageApi.loading('Đã tạo tác vụ import, hệ thống đang xử lý...', 2)
      }
      setFile(null)
    } catch (err: any) {
      messageApi.error(err?.message || 'Không thể import tài liệu')
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      {contextHolder}
      <nav className="nav">
        <div className="container" style={{ display: 'flex', gap: 16 }}>
          <Link
            to="/"
            style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'inherit', textDecoration: 'none' }}
          >
            <HomeOutlined /> <span>Trang chủ</span>
          </Link>
          <Link
            to="/chat"
            style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'inherit', textDecoration: 'none' }}
          >
            <FileTextOutlined /> <span>Chatbot</span>
          </Link>
        </div>
      </nav>

      <div className="container" style={{ paddingTop: 32, paddingBottom: 64, maxWidth: 640 }}>
        <Card
          title={<Space align="center"><UploadOutlined /> <span>Import tài liệu pháp lý</span></Space>}
        >
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
            message="Chỉ cần chọn file PDF/DOCX, hệ thống sẽ tự tạo mã và trích toàn bộ nội dung."
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label
                className="ant-btn"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 8, cursor: 'pointer' }}
              >
                <UploadOutlined /> Chọn file
                <input
                  type="file"
                  accept=".pdf,.docx"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const selected = e.target.files?.[0] || null
                    setFile(selected)
                    if (selected) {
                      messageApi.success(`Đã chọn ${selected.name}`)
                    }
                  }}
                />
              </label>
              <div style={{ fontSize: 13, color: 'var(--color-muted)' }}>Khuyến nghị dung lượng dưới 50MB</div>
              {file && (
                <div style={{ fontSize: 13, color: 'var(--color-muted)', marginTop: 4 }}>
                  Đã chọn: <strong>{file.name}</strong>
                </div>
              )}
            </div>

            <Button
              type="primary"
              icon={<FileDoneOutlined />}
              onClick={handleUpload}
              loading={uploading}
              disabled={!file}
            >
              Import tài liệu
            </Button>
          </div>

          {job && (
            <Card type="inner" title="Tiến độ import" style={{ marginTop: 24 }}>
              <p>
                <Tag color="blue">{job.code}</Tag> {job.filename}
              </p>
              <p>
                Trạng thái: <strong>{job.status}</strong> • Tiến độ: <strong>{job.progress}%</strong>
              </p>
              {job.status === 'failed' && job.error_message && (
                <Alert type="error" showIcon message={job.error_message} style={{ marginTop: 16 }} />
              )}
            </Card>
          )}

          {result && result.document && (
            <Card type="inner" title="Kết quả import" style={{ marginTop: 24 }}>
              <p>
                <Tag color="blue">{result.document?.code}</Tag> {result.document?.title}
              </p>
              <p>
                Số đoạn nội dung: <strong>{result.stats?.sections ?? 0}</strong> • Ảnh trích xuất:{' '}
                <strong>{result.stats?.images ?? 0}</strong>
              </p>
              {result.document?.uploaded_file_url && (
                <p>
                  File gốc:{' '}
                  <a href={result.document.uploaded_file_url} target="_blank" rel="noopener noreferrer">
                    tải xuống
                  </a>
                </p>
              )}
            </Card>
          )}
        </Card>
      </div>
    </>
  )
}

