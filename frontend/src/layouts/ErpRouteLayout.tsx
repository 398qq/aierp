import { useEffect } from 'react';
import { Spin } from 'antd';
import { ProLayout } from '@ant-design/pro-components';
import { Outlet, Navigate, useLocation } from '@umijs/max';
import { useAuthStore } from '@/store/auth';
import { menuItems } from './menuConfig';

export default function ErpRouteLayout(): React.JSX.Element {
  const username = useAuthStore((s) => s.username);
  const loading = useAuthStore((s) => s.loading);
  const init = useAuthStore((s) => s.init);
  const location = useLocation();

  useEffect(() => {
    void init();
  }, [init]);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />;
  }
  if (!username) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ProLayout
      layout="mix"
      title="AIERP"
      logo="/icon-192.png"
      location={location}
      menu={{ type: 'group', items: menuItems }}
      menuDataRender={() => menuItems}
      contentWidth="Fluid"
      siderWidth={224}
      fixedHeader
    >
      <Outlet />
    </ProLayout>
  );
}