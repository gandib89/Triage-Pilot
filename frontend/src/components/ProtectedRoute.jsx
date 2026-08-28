import { Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAccessToken, useRole } from "../auth";
import { refreshAccessToken } from "../api";

function ProtectedRoute({ children, roles, redirectTo = '/tickets' }) {
    const token = useAccessToken();
    const role = useRole();
    // A page load/reload starts with no access token in memory (it's never
    // persisted) — recover it from the httpOnly refresh cookie before
    // deciding this visitor is signed out. Nothing to recover if we already
    // have a token.
    const [refreshDone, setRefreshDone] = useState(Boolean(token));

    useEffect(() => {
        if (token) return;
        let cancelled = false;
        refreshAccessToken().finally(() => !cancelled && setRefreshDone(true));
        return () => {
            cancelled = true;
        };
    }, [token]);

    if (!token && !refreshDone) {
        return (
            <div className="flex min-h-[100dvh] items-center justify-center">
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">Authorizing</span>
            </div>
        );
    }

    if (!token) {
        return <Navigate to="/login" />;
    }

    if (roles && !roles.includes(role)) {
        return <Navigate to={redirectTo} />;
    }

    return children;
}

export default ProtectedRoute;
