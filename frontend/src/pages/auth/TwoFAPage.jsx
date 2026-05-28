import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { verify2fa } from "../../api/auth";
import Spinner from "../../components/common/Spinner";

export default function TwoFAPage() {
  const navigate  = useNavigate();
  const setUser   = useAuthStore((s) => s.setUser);
  const [code, setCode]   = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await verify2fa(code);
      setUser(res);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error?.message || "Invalid code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Two-factor auth</h1>
          <p className="text-sm text-gray-500 mt-1">
            Enter the 6-digit code from your authenticator app
          </p>
        </div>

        {error && (
          <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="w-full border border-gray-300 rounded-lg px-3 py-3 text-center text-2xl tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="000000"
            autoFocus
          />

          <button
            type="submit"
            disabled={loading || code.length !== 6}
            className="w-full bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? <Spinner size="sm" /> : null}
            {loading ? "Verifying…" : "Verify"}
          </button>
        </form>
      </div>
    </div>
  );
}