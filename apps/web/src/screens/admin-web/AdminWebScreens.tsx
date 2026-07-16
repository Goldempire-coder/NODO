"use client";

import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { AuditLogs } from "./AdminAuditScreens";
import { Businesses, BusinessDetail } from "./AdminBusinessScreens";
import { BusinessIntake, BusinessIntakeDetail } from "./AdminBusinessIntakeScreens";
import { CreditAdjustments, CreditDetail, CreditPurchases } from "./AdminCreditScreens";
import { DisputeDetail, Disputes, OrderDetail, Orders } from "./AdminOrderDisputeScreens";
import { Dashboard, Jobs, Metrics } from "./AdminOverviewScreens";
import { SupportTickets } from "./AdminSupportScreens";
import { StaffCenter, StaffDetail, StaffInvite } from "./AdminStaffScreens";
import { UserDetail, Users } from "./AdminUserScreens";

export function AdminWebScreens({ model }: { model: AdminWebModel }) {
  if (!model.adminReadable) {
    return (
      <section className="admin-web-panel">
        <h2>Acceso denegado</h2>
        <p>Esta superficie es solo para admin, super_admin o support activo. El backend conserva la autoridad final.</p>
      </section>
    );
  }

  return (
    <div className="admin-web-content">
      {model.view === "dashboard" ? <Dashboard model={model} /> : null}
      {model.view === "metrics" ? <Metrics model={model} /> : null}
      {model.view === "businesses" ? <Businesses model={model} /> : null}
      {model.view === "business-detail" ? <BusinessDetail model={model} /> : null}
      {model.view === "users" ? <Users model={model} /> : null}
      {model.view === "user-detail" ? <UserDetail model={model} /> : null}
      {model.view === "orders" ? <Orders model={model} /> : null}
      {model.view === "order-detail" ? <OrderDetail model={model} /> : null}
      {model.view === "disputes" ? <Disputes model={model} /> : null}
      {model.view === "dispute-detail" ? <DisputeDetail model={model} /> : null}
      {model.view === "audit-logs" ? <AuditLogs model={model} /> : null}
      {model.view === "credit-purchases" ? <CreditPurchases model={model} /> : null}
      {model.view === "credit-detail" ? <CreditDetail model={model} /> : null}
      {model.view === "credit-adjustments" ? <CreditAdjustments model={model} /> : null}
      {model.view === "jobs" ? <Jobs model={model} /> : null}
      {model.view === "intake" ? <BusinessIntake model={model} /> : null}
      {model.view === "intake-detail" ? <BusinessIntakeDetail model={model} /> : null}
      {model.view === "support" ? <SupportTickets model={model} /> : null}
      {model.view === "staff" ? <StaffCenter model={model} /> : null}
      {model.view === "staff-detail" ? <StaffDetail model={model} /> : null}
      {model.view === "staff-invite" ? <StaffInvite model={model} /> : null}
    </div>
  );
}
