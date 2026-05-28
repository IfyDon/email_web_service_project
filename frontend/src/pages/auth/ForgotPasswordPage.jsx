import { useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../../api/auth";
import Spinner from "../../components/common/Spinner";

export default function ForgotPasswordPage() {
  const [email, setEmail]     = useState("");
  const [sent, setSent]       = useState(false);
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Reset password</h1>
          <p className="text-sm text-gray-500 mt-1">
            We'll send a reset link to your email
          </p>
        </div>

        {sent ? (
          <div className="text-center space-y-4">
            <div className="text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
              Check your inbox — a reset link has been sent to <strong>{email}</strong>.
            </div>
            <Link to="/login" className="text-indigo-600 text-sm hover:underline">
              Back to login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="you@example.com"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading ? <Spinner size="sm" /> : null}
              {loading ? "Sending…" : "Send reset link"}
            </button>

            <p className="text-center text-sm text-gray-500">
              <Link to="/login" className="text-indigo-600 hover:underline">
                Back to login
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}