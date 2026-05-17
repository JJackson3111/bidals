"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { UserPlus } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { ApiError } from "@/lib/api";
import type { UserRole } from "@/lib/types";

export default function RegisterPage() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState<Extract<UserRole, "bidder" | "seller">>("bidder");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await register({ username, email, password, account_type: accountType });
      setSuccess("Account created. You can login now.");
      setPassword("");
    } catch (err) {
      setError(ApiError.messageFrom(err, "Unable to register."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell auth-shell">
      <section className="page-heading">
        <span className="eyebrow">Join BIDALS</span>
        <h1>Register</h1>
      </section>
      <form className="form-panel" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input id="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
          </div>
          <div className="form-field">
            <label htmlFor="email">Email</label>
            <input id="email" autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div className="form-field">
            <label htmlFor="role">Account type</label>
            <select id="role" value={accountType} onChange={(event) => setAccountType(event.target.value as "bidder" | "seller")}>
              <option value="bidder">Bidder</option>
              <option value="seller">Seller</option>
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input id="password" autoComplete="new-password" minLength={8} required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
        </div>
        {error ? <div className="form-error" role="alert">{error}</div> : null}
        {success ? <div className="form-success" role="status">{success}</div> : null}
        <button className="primary-button" disabled={isSubmitting} type="submit">
          <UserPlus size={18} aria-hidden="true" />
          {isSubmitting ? "Creating" : "Create account"}
        </button>
        <p>
          Already registered? <Link className="text-link" href="/login">Login</Link>
        </p>
      </form>
    </main>
  );
}
