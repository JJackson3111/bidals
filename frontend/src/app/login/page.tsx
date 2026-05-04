"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(username, password);
      router.push("/auctions");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to login.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell auth-shell">
      <section className="page-heading">
        <span className="eyebrow">Welcome back</span>
        <h1>Login</h1>
      </section>
      <form className="form-panel" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input id="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input id="password" autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
        </div>
        {error ? <div className="form-error" role="alert">{error}</div> : null}
        <button className="primary-button" disabled={isSubmitting} type="submit">
          <LogIn size={18} aria-hidden="true" />
          {isSubmitting ? "Logging in" : "Login"}
        </button>
        <p>
          New to BIDALS? <Link className="text-link" href="/register">Create an account</Link>
        </p>
      </form>
    </main>
  );
}

