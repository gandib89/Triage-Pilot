import { jwtDecode } from 'jwt-decode'
import { ACCESS_TOKEN } from './constants'

export const STAFF_ROLES = ['agent', 'admin']

export function getRole() {
    const token = localStorage.getItem(ACCESS_TOKEN)
    if (!token) return null
    try {
        return jwtDecode(token).role || null
    } catch {
        return null
    }
}

export function isStaff() {
    return STAFF_ROLES.includes(getRole())
}
