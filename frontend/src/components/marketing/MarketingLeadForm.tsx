"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";

type MarketingLeadFormProps = {
  kind: "demo" | "contact";
};

export function MarketingLeadForm({ kind }: MarketingLeadFormProps) {
  const [isSubmitted, setIsSubmitted] = useState(false);
  const isDemo = kind === "demo";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO: Connect this frontend-only form to an approved backend or email workflow.
    setIsSubmitted(true);
  }

  return (
    <form className="marketing-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="form-field">
          <label htmlFor={`${kind}-name`}>Name</label>
          <input id={`${kind}-name`} name="name" autoComplete="name" required type="text" />
        </div>
        <div className="form-field">
          <label htmlFor={`${kind}-email`}>Work email</label>
          <input id={`${kind}-email`} name="email" autoComplete="email" required type="email" />
        </div>
        <div className="form-field">
          <label htmlFor={`${kind}-organisation`}>Organisation</label>
          <input id={`${kind}-organisation`} name="organisation" autoComplete="organization" required type="text" />
        </div>
        {isDemo ? (
          <div className="form-field">
            <label htmlFor="demo-focus">Fundraising focus</label>
            <select id="demo-focus" name="focus" defaultValue="auctions">
              <option value="auctions">Auctions</option>
              <option value="raffles">Raffles</option>
              <option value="donations">Donations</option>
              <option value="multi-channel">Multi-channel event</option>
            </select>
          </div>
        ) : null}
        <div className="form-field marketing-form-wide">
          <label htmlFor={`${kind}-message`}>{isDemo ? "What are you planning?" : "Message"}</label>
          <textarea
            id={`${kind}-message`}
            name="message"
            placeholder={isDemo ? "Tell us about your event size, timeline, and team." : "How can we help?"}
            required
          />
        </div>
      </div>
      {isSubmitted ? (
        <div className="form-success" role="status">
          Thanks. This form is currently frontend-only, so no message has been sent yet.
        </div>
      ) : null}
      <button className="primary-button marketing-form-submit" type="submit">
        {isDemo ? "Request demo" : "Send message"}
        <Send size={17} aria-hidden="true" />
      </button>
    </form>
  );
}
