import { useState } from 'react';

export default function DataVizCard({ tool, result }) {
  if (!result) return null;

  if (tool === 'query_order' && result) {
    return <OrderCard data={result} />;
  }

  if (tool === 'query_inventory' && result) {
    return <InventoryCard data={result} />;
  }

  if (tool === 'query_orders' && Array.isArray(result)) {
    return <OrderList data={result} />;
  }

  return <pre className="data-viz-fallback">{JSON.stringify(result, null, 2)}</pre>;
}

function OrderCard({ data }) {
  const order = data.order || data;
  return (
    <div className="data-viz-card order-card">
      <h3 className="card-title">订单详情</h3>
      <table className="data-table">
        <tbody>
          {order.id && <tr><th>订单ID</th><td>{order.id}</td></tr>}
          {order.status && <tr><th>状态</th><td>{order.status}</td></tr>}
          {order.customer && <tr><th>客户</th><td>{order.customer}</td></tr>}
          {order.product && <tr><th>商品</th><td>{order.product}</td></tr>}
          {order.quantity && <tr><th>数量</th><td>{order.quantity}</td></tr>}
          {order.amount && <tr><th>金额</th><td>{order.amount}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function InventoryCard({ data }) {
  const inv = data.inventory || data;
  return (
    <div className="data-viz-card inventory-card">
      <h3 className="card-title">库存信息</h3>
      <table className="data-table">
        <tbody>
          {inv.sku && <tr><th>SKU</th><td>{inv.sku}</td></tr>}
          {inv.name && <tr><th>名称</th><td>{inv.name}</td></tr>}
          {inv.quantity != null && <tr><th>当前数量</th><td>{inv.quantity}</td></tr>}
          {inv.reserved != null && <tr><th>预留</th><td>{inv.reserved}</td></tr>}
          {inv.available != null && <tr><th>可用量</th><td>{inv.available}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function OrderList({ data }) {
  return (
    <div className="data-viz-card order-list-card">
      <h3 className="card-title">订单列表 ({data.length})</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>状态</th>
            <th>商品</th>
            <th>数量</th>
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 10).map((order, i) => (
            <tr key={i}>
              <td>{order.id || '-'}</td>
              <td>{order.status || '-'}</td>
              <td>{order.product || '-'}</td>
              <td>{order.quantity || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
