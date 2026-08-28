import { jwtDecode } from 'jwt-decode'
import { useSyncExternalStore } from 'react'

export const STAFF_ROLES = ['staff', 'admin']

// The access token lives only in memory — never localStorage — so a stolen
// XSS payload can't read it off disk. It's lost on page reload by design;
// ProtectedRoute recovers it via a silent /token/refresh/ call against the
// httpOnly refresh cookie. A tiny external store (not React context) so
// api.js's axios interceptors, which aren't components, can read/write it too.
let accessToken = null
const listeners = new Set()

export function getAccessToken() {
    return accessToken
}

export function setAccessToken(token) {
    accessToken = token
    listeners.forEach((listener) => listener())
}

function subscribe(onChange) {
    listeners.add(onChange)
    return () => listeners.delete(onChange)
}

export function useAccessToken() {
    return useSyncExternalStore(subscribe, getAccessToken)
}

function decodeRole(token) {
    if (!token) return null
    try {
        return jwtDecode(token).role || null
    } catch {
        return null
    }
}

export function getRole() {
    return decodeRole(getAccessToken())
}

export function isStaff() {
    return STAFF_ROLES.includes(getRole())
}

export function useRole() {
    return decodeRole(useAccessToken())
}

export function useIsStaff() {
    return STAFF_ROLES.includes(useRole())
}
