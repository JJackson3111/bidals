"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { FundraisingFocus } from "@/lib/types";

type MarketingLeadFormProps = {
  kind: "demo" | "contact";
};

export function MarketingLeadForm({ kind }: MarketingLeadFormProps) {
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const isDemo = kind === "demo";
  const isSubmitting = status === "submitting";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    setStatus("submitting");
    setErrorMessage("");

    try {
      await api.submitLeadRequest({
        name: formValue(formData, "name"),
        email: formValue(formData, "email"),
        organisation: formValue(formData, "organisation"),
        fundraising_focus: formValue(formData, "fundraising_focus") as FundraisingFocus,
        message: formValue(formData, "message"),
        source_page: isDemo ? "book_demo" : "contact",
        website: formValue(formData, "website"),
      });
      form.reset();
      setStatus("success");
    } catch (error) {
      setErrorMessage(
        ApiError.messageFrom(
          error,
          "We could not submit your request. Please check the details and try again.",
        ),
      );
      setStatus("error");
    }
  }

  return (
    <form className="marketing-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="form-field">
          <label htmlFor={`${kind}-name`}>Name</label>
          <input id={`${kind}-name`} name="name" autoComplete="name" maxLength={120} required type="text" />
        </div>
        <div className="form-field">
          <label htmlFor={`${kind}-email`}>Work email</label>
          <input id={`${kind}-email`} name="email" autoComplete="email" maxLength={254} required type="email" />
        </div>
        <div className="form-field">
          <label htmlFor={`${kind}-organisation`}>Organisation</label>
          <input
            id={`${kind}-organisation`}
            name="organisation"
            autoComplete="organization"
            maxLength={160}
            required
            type="text"
          />
        </div>
        <div className="form-field">
          <label htmlFor={`${kind}-focus`}>Fundraising focus</label>
          <select id={`${kind}-focus`} name="fundraising_focus" defaultValue={isDemo ? "auctions" : "general_enquiry"} required>
            <option value="auctions">Auctions</option>
            <option value="raffles">Raffles</option>
            <option value="donations">Donations</option>
            <option value="multi_channel">Multi-channel event</option>
            <option value="general_enquiry">General enquiry</option>
            <option value="partnership">Partnership</option>
            <option value="support">Support</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="form-field marketing-form-wide">
          <label htmlFor={`${kind}-message`}>Tell us about your fundraising plans</label>
          <textarea
            id={`${kind}-message`}
            name="message"
            maxLength={2000}
            placeholder={
              isDemo
                ? "Share your event size, timeline, fundraising format and team needs."
                : "Share your campaign, support need or partnership context."
            }
            required
          />
        </div>
        <div className="marketing-honeypot" aria-hidden="true">
          <label htmlFor={`${kind}-website`}>Website</label>
          <input id={`${kind}-website`} name="website" autoComplete="off" tabIndex={-1} type="text" />
        </div>
      </div>
      {status === "success" ? (
        <div className="form-success marketing-form-status" role="status">
          We&apos;ll review your request and come back to you directly.
        </div>
      ) : null}
      {status === "error" ? (
        <div className="form-error marketing-form-status" role="alert">
          {errorMessage}
        </div>
      ) : null}
      <button className="primary-button marketing-form-submit" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Sending..." : isDemo ? "Request demo" : "Send message"}
        <Send size={17} aria-hidden="true" />
      </button>
    </form>
  );
}

function formValue(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}
