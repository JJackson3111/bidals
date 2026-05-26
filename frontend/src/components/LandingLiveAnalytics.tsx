"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { BarChart3, Bell, TrendingUp } from "lucide-react";

const demoTotals = {
  auctionCycleBaseRaised: 11275,
  donationsTotal: 15250,
  goalTotal: 20000,
  rafflesTotal: 5600,
};
const baseActiveBidders = 52;
const baseTotalBids = 247;
const cycleDelayMs = 6200;
const initialActiveIndex = 3;
const initialStatIncrements = 2;

const bidEvents = [
  {
    text: "New bid on Vintage Camera",
    time: "just now",
    amount: 250,
  },
  {
    text: "Bid increased on Watch Set",
    time: "1m ago",
    amount: 500,
  },
  {
    text: "New bid on Art Print",
    time: "3m ago",
    amount: 125,
  },
  {
    text: "Final bid received on Wine Selection",
    time: "5m ago",
    amount: 750,
  },
  {
    text: "New bid on Designer Handbag",
    time: "7m ago",
    amount: 300,
  },
];

function formatPounds(value: number) {
  return `\u00a3${value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

function formatBidAmount(value: number) {
  return `+\u00a3${value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

function formatPlainIncrease(value: number) {
  return `+${value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

function easeOutCubic(value: number) {
  return 1 - Math.pow(1 - value, 3);
}

function getAuctionRaisedForEvent(index: number) {
  const bidIncrease = bidEvents.slice(0, index + 1).reduce((total, event) => total + event.amount, 0);

  return demoTotals.auctionCycleBaseRaised + bidIncrease;
}

function getProgress(auctionRaised: number) {
  return Math.floor((auctionRaised / demoTotals.goalTotal) * 100);
}

export function LandingLiveAnalytics() {
  const [activeIndex, setActiveIndex] = useState(initialActiveIndex);
  const [auctionRaised, setAuctionRaised] = useState(getAuctionRaisedForEvent(initialActiveIndex));
  const [totalBids, setTotalBids] = useState(baseTotalBids + initialStatIncrements);
  const [activeBidders, setActiveBidders] = useState(baseActiveBidders + initialStatIncrements);
  const [motionKey, setMotionKey] = useState(initialActiveIndex);
  const activeEvent = bidEvents[activeIndex];
  const amountLabel = formatBidAmount(activeEvent.amount);
  const activeDeltaLabel = formatPlainIncrease(activeEvent.amount);
  const progress = getProgress(auctionRaised);
  const totalAllSources = auctionRaised + demoTotals.donationsTotal + demoTotals.rafflesTotal;
  const travelStyle = { "--activity-row": activeIndex } as CSSProperties;

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animationFrame = 0;
    let interval = 0;
    let currentIndex = initialActiveIndex;
    let currentAuctionRaised = getAuctionRaisedForEvent(initialActiveIndex);
    let currentTotalBids = baseTotalBids + initialStatIncrements;
    let currentActiveBidders = baseActiveBidders + initialStatIncrements;

    if (motionQuery.matches) {
      return undefined;
    }

    const animateTotal = (from: number, to: number) => {
      const startedAt = performance.now();
      const duration = 1250;

      const tick = (now: number) => {
        const elapsed = Math.min((now - startedAt) / duration, 1);
        const eased = easeOutCubic(elapsed);
        setAuctionRaised(Math.round(from + (to - from) * eased));

        if (elapsed < 1) {
          animationFrame = window.requestAnimationFrame(tick);
        }
      };

      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(tick);
    };

    const showNextBid = () => {
      currentIndex = (currentIndex + 1) % bidEvents.length;

      if (currentIndex === 0 && currentAuctionRaised !== demoTotals.auctionCycleBaseRaised) {
        currentAuctionRaised = demoTotals.auctionCycleBaseRaised;
        currentTotalBids = baseTotalBids;
        currentActiveBidders = baseActiveBidders;
        setAuctionRaised(demoTotals.auctionCycleBaseRaised);
      }

      const nextTotal = getAuctionRaisedForEvent(currentIndex);
      currentTotalBids += 1;
      currentActiveBidders = Math.min(60, currentActiveBidders + 1);

      setActiveIndex(currentIndex);
      setTotalBids(currentTotalBids);
      setActiveBidders(currentActiveBidders);
      setMotionKey((key) => key + 1);
      animateTotal(currentAuctionRaised, nextTotal);
      currentAuctionRaised = nextTotal;
    };

    interval = window.setInterval(showNextBid, cycleDelayMs);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="seller-preview-grid seller-preview-grid-live">
      <article className="seller-preview-panel">
        <div className="seller-preview-title">
          <div className="landing-icon-box compact">
            <BarChart3 size={20} aria-hidden="true" />
          </div>
          <h3>Live analytics</h3>
        </div>
        <div className="auction-progress-module" aria-label="Auction progress">
          <div className="auction-progress-header">
            <div>
              <span>Auction progress</span>
              <strong>{formatPounds(auctionRaised)} raised</strong>
            </div>
            <small>
              {progress}% of {formatPounds(demoTotals.goalTotal)} goal
            </small>
          </div>
          <div
            className="auction-progress-track"
            role="progressbar"
            aria-label="Auction progress toward goal"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <span className="auction-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="latest-sale-badge" key={`sale-${motionKey}`}>
            {amountLabel} latest sale
          </div>
        </div>
        <div className="seller-metric-list">
          <div>
            <span>Total bids</span>
            <div className="metric-value-group">
              <strong>{totalBids}</strong>
              <span className="metric-delta" key={`bids-${motionKey}`}>
                ↑ +1
              </span>
            </div>
          </div>
          <div>
            <span>Active bidders</span>
            <div className="metric-value-group">
              <strong>{activeBidders}</strong>
              <span className="metric-delta" key={`bidders-${motionKey}`}>
                ↑ +1
              </span>
            </div>
          </div>
          <div className="seller-value-row">
            <div className="seller-value-copy">
              <span>Total value (All sources)</span>
              <div className="source-breakdown" aria-label="All sources breakdown">
                <span>Auction {formatPounds(auctionRaised)}</span>
                <span>Donations {formatPounds(demoTotals.donationsTotal)}</span>
                <span>Raffles {formatPounds(demoTotals.rafflesTotal)}</span>
              </div>
            </div>
            <div className="metric-value-group seller-value-total">
              <strong>{formatPounds(totalAllSources)}</strong>
              <span className="metric-delta" key={`value-${motionKey}`}>
                ↑ {activeDeltaLabel}
              </span>
            </div>
          </div>
        </div>
        <div className="seller-live-note">
          <span aria-hidden="true" />
          <small>All totals update in real-time</small>
        </div>
      </article>

      <article className="seller-preview-panel">
        <div className="seller-preview-title">
          <div className="landing-icon-box compact">
            <Bell size={20} aria-hidden="true" />
          </div>
          <h3>Live activity</h3>
        </div>
        <div className="activity-list">
          {bidEvents.map((activity, index) => {
            const isActive = index === activeIndex;
            const rowAmount = formatBidAmount(activity.amount);

            return (
              <div className={`activity-row bid-activity-row${isActive ? " is-active" : ""}`} key={activity.text}>
                <div className="activity-icon">
                  <TrendingUp size={16} aria-hidden="true" />
                </div>
                <div className="activity-copy">
                  <span>{activity.text}</span>
                  <small>{activity.time}</small>
                </div>
                <span className="activity-amount">{rowAmount}</span>
                {isActive ? (
                  <span className="activity-row-pill" key={`row-pill-${motionKey}`} aria-hidden="true">
                    {rowAmount}
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      </article>

      <span className="bid-travel-pill" key={`travel-${motionKey}`} style={travelStyle} aria-hidden="true">
        {amountLabel}
      </span>
    </div>
  );
}
