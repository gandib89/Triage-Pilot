import { Navigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";
import { REFRESH_TOKEN, ACCESS_TOKEN } from "../constants";
import { useState, useEffect } from "react";
import api from "../api";


function ProtectedRoute({ children, roles, redirectTo = '/tickets' }) {
    const [isAuthorized, setIsAuthorized] = useState(null);
    const [role, setRole] = useState(null);

    useEffect(() => {
        auth().catch(() => setIsAuthorized(false))
    }, [])

    const refreshToken = async () => {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN);
        try {
            const res = await api.post("/token/refresh/", {
                refresh: refreshToken,
            });
            if (res.status === 200) {
                localStorage.setItem(ACCESS_TOKEN, res.data.access)
                setRole(jwtDecode(res.data.access).role || null)
                setIsAuthorized(true)
            } else {
                setIsAuthorized(false)
            }
        } catch (error) {
            console.log(error);
            setIsAuthorized(false);
        }
    };

    const auth = async () => {
        const token = localStorage.getItem(ACCESS_TOKEN);
        if (!token) {
            setIsAuthorized(false);
            return;
        }
        const decoded = jwtDecode(token);
        const tokenExpiration = decoded.exp;
        const now = Date.now() / 1000;

        if (tokenExpiration < now) {
            await refreshToken();
        } else {
            setRole(decoded.role || null)
            setIsAuthorized(true);
        }
    };

    if (isAuthorized === null) {
        return (
            <div className="flex min-h-[100dvh] items-center justify-center">
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">Authorizing</span>
            </div>
        );
    }

    if (!isAuthorized) {
        return <Navigate to="/login" />;
    }

    if (roles && !roles.includes(role)) {
        return <Navigate to={redirectTo} />;
    }

    return children;
}

export default ProtectedRoute;
