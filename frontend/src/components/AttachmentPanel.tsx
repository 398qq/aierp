import { useEffect, useState } from "react";
import { Button, Empty, List, message, Modal, Space, Spin, Typography, Upload } from "antd";
import { DeleteOutlined, DownloadOutlined, FileOutlined, UploadOutlined } from "@ant-design/icons";
import { deleteDocument, downloadDocument, getDocuments, uploadDocument } from "../api";
import type { Document } from "../types";

const { Text } = Typography;

interface Props {
  entityType: string;
  entityId: number;
}

export default function AttachmentPanel({ entityType, entityId }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getDocuments(entityType, entityId);
      setDocs((resp.data.data as Document[]) || []);
    } catch {
      // entity may not exist yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [entityType, entityId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocument(entityType, entityId, file);
      message.success("上传成功");
      load();
    } catch {
      message.error("上传失败");
      return false;
    } finally {
      setUploading(false);
    }
    return false; // prevent default Upload behavior
  };

  const handleDownload = async (doc: Document) => {
    try {
      const resp = await downloadDocument(doc.id);
      const url = URL.createObjectURL(new Blob([resp.data as BlobPart]));
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载失败");
    }
  };

  const handleDelete = (doc: Document) => {
    Modal.confirm({
      title: "确认删除",
      content: `确定要删除文件 "${doc.filename}" 吗？`,
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteDocument(doc.id);
          message.success("已删除");
          load();
        } catch {
          message.error("删除失败");
        }
      },
    });
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const fileIcon = (mime: string | null) => {
    if (!mime) return <FileOutlined />;
    if (mime.startsWith("image/")) return <FileOutlined style={{ color: "#52c41a" }} />;
    if (mime.includes("pdf")) return <FileOutlined style={{ color: "#ff4d4f" }} />;
    if (mime.includes("spreadsheet") || mime.includes("excel"))
      return <FileOutlined style={{ color: "#1677ff" }} />;
    return <FileOutlined />;
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Upload
          accept="*"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
        >
          <Button icon={<UploadOutlined />} loading={uploading}>
            上传文件
          </Button>
        </Upload>
        <Text type="secondary">支持 PDF / Word / Excel / 图片，最大 10MB</Text>
      </Space>

      {loading ? (
        <Spin />
      ) : docs.length === 0 ? (
        <Empty description="暂无附件" />
      ) : (
        <List
          size="small"
          dataSource={docs}
          renderItem={(doc) => (
            <List.Item
              actions={[
                <Button
                  key="download"
                  type="link"
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownload(doc)}
                />,
                <Button
                  key="delete"
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(doc)}
                />,
              ]}
            >
              <List.Item.Meta
                avatar={fileIcon(doc.mime_type)}
                title={
                  <Button type="link" size="small" onClick={() => handleDownload(doc)}>
                    {doc.filename}
                  </Button>
                }
                description={
                  <Space size="middle">
                    <span>{formatSize(doc.file_size)}</span>
                    {doc.uploader_name && <span>上传者: {doc.uploader_name}</span>}
                    <span>{doc.created_at?.slice(0, 10)}</span>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
