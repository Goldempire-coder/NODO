import type { PublicUser } from "../../types/auth";

export function canMutateAdmin(user: PublicUser) {
  return user.status === "active" && (user.role === "admin" || user.role === "super_admin");
}

export function canReadAdmin(user: PublicUser) {
  return user.status === "active" && (user.role === "admin" || user.role === "super_admin" || user.role === "support");
}
