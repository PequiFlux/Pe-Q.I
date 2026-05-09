from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --green-50: #ecfdf5;
            --green-100: #d8f9e9;
            --green-400: #34d399;
            --green-500: #22c98b;
            --green-700: #087d55;
            --green-800: #075f45;
            --green-900: #063d31;
            --pequi-50: #fff9e6;
            --pequi-400: #f5c542;
            --pequi-700: #8a5a00;
            --red-50: #fff1f2;
            --red-600: #dc2626;
            --blue-50: #eff6ff;
            --blue-700: #1d4ed8;
            --purple-50: #f5f3ff;
            --purple-700: #6d28d9;
            --slate-50: #f8fafc;
            --slate-100: #f1f5f9;
            --slate-200: #e2e8f0;
            --slate-500: #64748b;
            --slate-700: #334155;
            --slate-900: #0f172a;
            --ink: #10231d;
            --muted: #66746f;
            --line: rgba(16, 35, 29, 0.10);
            --shadow: 0 18px 42px rgba(15, 23, 42, 0.10);
          }
          .stApp {
            color: var(--ink);
            background:
              linear-gradient(135deg, #f7fbf5 0%, #f3f8ef 46%, #f8fafc 100%);
          }
          header[data-testid="stHeader"],
          div[data-testid="stToolbar"],
          div[data-testid="stDecoration"] {
            display: none;
          }
          .block-container {
            max-width: 1500px;
            padding-top: 8px;
            padding-bottom: 40px;
          }
          section[data-testid="stSidebar"] {
            background:
              linear-gradient(180deg, rgba(52, 211, 153, 0.13), rgba(4, 120, 87, 0.02)),
              linear-gradient(180deg, var(--green-900), #041f19);
          }
          section[data-testid="stSidebar"] label,
          section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] span,
          section[data-testid="stSidebar"] li {
            color: rgba(236, 255, 248, 0.82);
          }
          section[data-testid="stSidebar"] button p {
            color: var(--green-900);
            font-weight: 900;
          }
          .brand {
            display: grid;
            grid-template-columns: 48px 1fr;
            gap: 12px;
            align-items: center;
            padding: 8px 2px 18px;
            margin-bottom: 18px;
            border-bottom: 1px solid rgba(255,255,255,0.10);
          }
          .brand-mark {
            width: 48px;
            height: 48px;
            border-radius: 15px;
            background:
              radial-gradient(circle at 70% 25%, var(--pequi-400) 0 16%, transparent 17%),
              linear-gradient(145deg, var(--green-400), var(--green-700));
            box-shadow: 0 18px 36px rgba(52, 211, 153, 0.28);
          }
          .brand h1 {
            margin: 0;
            color: #fff;
            font-size: 20px;
            line-height: 1.05;
          }
          .brand p {
            margin: 4px 0 0;
            color: rgba(236,255,248,0.64);
            font-size: 12px;
          }
          .side-card {
            margin-top: 14px;
            padding: 15px;
            border-radius: 16px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
          }
          .side-card.compact p,
          .side-card li {
            font-size: 12px;
            line-height: 1.45;
          }
          .side-kicker {
            color: rgba(236,255,248,0.56);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .hero {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(340px, 0.45fr);
            gap: 14px;
            align-items: center;
            padding: 18px 20px;
            margin-bottom: 10px;
            border-radius: 16px;
            color: #fff;
            background:
              linear-gradient(135deg, rgba(6,61,49,0.98), rgba(15,23,42,0.98));
            box-shadow: 0 18px 38px rgba(15, 23, 42, 0.16);
          }
          .eyebrow {
            color: rgba(255,255,255,0.66);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .hero h1 {
            margin: 6px 0 0;
            max-width: 760px;
            font-size: 31px;
            line-height: 1.06;
            letter-spacing: 0;
          }
          .hero p {
            margin: 8px 0 0;
            max-width: 860px;
            color: rgba(255,255,255,0.72);
            font-size: 13px;
            line-height: 1.38;
          }
          .hero-proof {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
          }
          .hero-proof div {
            min-height: 62px;
            padding: 10px;
            border-radius: 10px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
          }
          .hero-proof strong {
            display: block;
            color: #fff;
            font-size: 17px;
            line-height: 1.05;
          }
          .hero-proof span {
            display: block;
            margin-top: 6px;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .section-title,
          .card-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin: 10px 0 10px;
          }
          .compact-title {
            margin-top: 0;
          }
          div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,0.80);
            box-shadow: 0 8px 20px rgba(15,23,42,0.05);
          }
          div[data-testid="stExpander"] summary {
            color: var(--green-800);
            font-weight: 900;
          }
          .section-title h2,
          .card-head h3 {
            margin: 0;
            letter-spacing: 0;
          }
          .section-title h2 {
            font-size: 22px;
          }
          .empty-state {
            margin-top: 10px;
            padding: 18px;
            border-radius: 18px;
            background: linear-gradient(145deg, #fff, var(--pequi-50));
            border: 1px solid rgba(245,197,66,0.38);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .empty-state strong {
            display: block;
            color: var(--ink);
            font-size: 18px;
          }
          .empty-state p {
            margin: 6px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .card-head h3 {
            font-size: 18px;
          }
          .section-title p,
          .card-head p {
            margin: 5px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .panel-title {
            margin: 0 0 8px;
            font-size: 13px;
            color: var(--green-800);
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .input-summary {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: -4px 0 12px;
          }
          .input-summary div,
          .status-card,
          .audit-step {
            border-radius: 14px;
            padding: 11px;
            background: rgba(255,255,255,0.76);
            border: 1px solid var(--line);
          }
          .input-summary strong,
          .status-card strong {
            display: block;
            font-size: 22px;
            line-height: 1;
          }
          .input-summary span,
          .status-card span {
            display: block;
            margin-top: 6px;
            color: var(--muted);
            font-size: 11px;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .run-strip {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            margin: 14px 0 10px;
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.76);
            border: 1px solid var(--line);
          }
          .run-strip strong,
          .run-strip span {
            margin-right: 10px;
            font-size: 13px;
          }
          .run-note {
            color: var(--muted);
            font-size: 12px;
          }
          .source-note {
            margin: 8px 0 10px;
            padding: 9px 11px;
            border-radius: 10px;
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--line);
            color: var(--muted);
            font-size: 12px;
            font-weight: 750;
          }
          .scenario-note {
            display: grid;
            gap: 4px;
            margin: 0 0 12px;
            padding: 11px 12px;
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(236,253,245,0.92), #fff);
            border: 1px solid var(--line);
          }
          .scenario-note strong,
          .scenario-note span,
          .scenario-note em {
            display: block;
          }
          .scenario-note strong {
            color: var(--green-800);
            font-size: 13px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
          }
          .scenario-note span,
          .scenario-note em {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.4;
          }
          .scenario-note em {
            font-style: normal;
            font-weight: 850;
          }
          div[data-testid="stButton"] button {
            border-radius: 10px;
            border: 1px solid rgba(34,201,139,0.30);
            background: #fff;
            color: var(--green-800);
            font-weight: 900;
          }
          div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(145deg, var(--green-700), var(--green-900));
            border-color: rgba(34,201,139,0.44);
            color: #fff;
          }
          div[data-testid="stButton"] button:hover {
            border-color: var(--green-700);
            color: var(--green-800);
          }
          div[data-testid="stButton"] button[kind="primary"]:hover {
            color: #fff;
          }
          .status-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 12px;
          }
          .status-card p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .decision-story {
            display: grid;
            grid-template-columns: minmax(360px, 0.92fr) minmax(0, 1.08fr);
            gap: 14px;
            align-items: stretch;
            margin: 2px 0 10px;
          }
          .queue-focus {
            margin: 2px 0 10px;
            padding: 14px;
            border-radius: 14px;
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .queue-stack {
            display: grid;
            gap: 7px;
          }
          .queue-card {
            display: grid;
            grid-template-columns: 58px minmax(0, 1fr) minmax(220px, 0.62fr) 74px;
            gap: 12px;
            align-items: center;
            min-height: 62px;
            padding: 11px 13px;
            border-radius: 12px;
            background: #fff;
            border: 1px solid var(--line);
            box-shadow: 0 8px 18px rgba(15,23,42,0.04);
          }
          .queue-card.promoted {
            border-color: rgba(34,201,139,0.42);
            background: linear-gradient(90deg, var(--green-50), #fff);
            transform: translateX(10px);
          }
          .queue-card.blocked {
            border-color: rgba(220,38,38,0.28);
            background: linear-gradient(90deg, var(--red-50), #fff);
          }
          .queue-card.waiting {
            background: linear-gradient(90deg, var(--slate-50), #fff);
          }
          .queue-rank {
            display: grid;
            place-items: center;
            width: 44px;
            height: 44px;
            border-radius: 14px;
            color: var(--green-800);
            background: var(--green-50);
            border: 1px solid rgba(34,201,139,0.22);
            font-size: 14px;
            font-weight: 950;
          }
          .queue-card.blocked .queue-rank {
            color: var(--red-600);
            background: var(--red-50);
            border-color: rgba(220,38,38,0.20);
          }
          .queue-card strong {
            display: block;
            color: var(--ink);
            font-size: 20px;
            line-height: 1.05;
          }
          .queue-card span,
          .queue-state small,
          .queue-after {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .queue-state em {
            display: block;
            color: var(--ink);
            font-size: 12px;
            font-style: normal;
            font-weight: 950;
            letter-spacing: 0.05em;
            text-transform: uppercase;
          }
          .queue-state small {
            display: block;
            margin-top: 4px;
          }
          .queue-after {
            justify-self: end;
            border-radius: 999px;
            padding: 7px 9px;
            background: var(--slate-50);
            border: 1px solid var(--line);
            font-weight: 900;
          }
          .decision-story.single {
            grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
          }
          .story-main {
            padding: 18px;
            border-radius: 14px;
            color: #fff;
            background: linear-gradient(135deg, #063d31, #0f172a);
            box-shadow: 0 18px 38px rgba(15,23,42,0.16);
          }
          .eyebrow.dark {
            color: rgba(255,255,255,0.68);
          }
          .story-main h2 {
            margin: 10px 0 10px;
            font-size: 30px;
            line-height: 1.04;
            letter-spacing: 0;
          }
          .story-main p,
          .story-main li {
            color: rgba(255,255,255,0.76);
            font-size: 13px;
            line-height: 1.42;
          }
          .story-main ul {
            margin: 10px 0 0;
            padding-left: 18px;
          }
          .story-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
          }
          .story-grid.compact {
            height: 100%;
          }
          .story-tile {
            min-width: 0;
            min-height: 154px;
            padding: 14px;
            border-radius: 14px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.90);
            box-shadow: 0 10px 24px rgba(15,23,42,0.06);
          }
          .story-tile.action {
            background: linear-gradient(145deg, var(--green-50), #fff);
            border-color: rgba(34,201,139,0.26);
          }
          .story-tile.proof {
            background: linear-gradient(145deg, var(--pequi-50), #fff);
            border-color: rgba(245,197,66,0.34);
          }
          .story-tile span {
            display: block;
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .story-tile strong {
            display: block;
            margin-top: 12px;
            overflow-wrap: anywhere;
            color: var(--ink);
            font-size: 25px;
            line-height: 1.05;
          }
          .story-tile p {
            margin: 10px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .narrative-card {
            min-height: 0;
          }
          .constraint-list {
            display: grid;
            gap: 10px;
            margin: 0;
            padding: 0;
            list-style: none;
          }
          .constraint-list li {
            padding: 12px;
            border-radius: 14px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .constraint-list strong,
          .constraint-list span {
            display: block;
          }
          .constraint-list strong {
            color: var(--green-800);
            font-size: 12px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .constraint-list span {
            margin-top: 5px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .input-package,
          .ticket-preview,
          .copilot-timeline,
          .tools-card {
            min-height: 0;
          }
          .package-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }
          .package-grid div,
          .mini-metrics div,
          .tool-badge {
            min-width: 0;
            border-radius: 14px;
            padding: 11px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .package-grid span,
          .mini-metrics span,
          .tool-badge span {
            display: block;
            margin-bottom: 6px;
            color: var(--muted);
            font-size: 10px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .package-grid strong,
          .mini-metrics strong,
          .tool-badge strong {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--ink);
            font-size: 13px;
          }
          .package-grid strong {
            overflow-wrap: anywhere;
            white-space: normal;
          }
          .mini-metrics strong,
          .tool-badge strong {
            white-space: nowrap;
          }
          .document-tile {
            display: grid;
            grid-template-columns: 74px minmax(0, 1fr);
            gap: 12px;
            align-items: center;
            padding: 12px;
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(236,253,245,0.88), rgba(255,255,255,0.95));
            border: 1px solid var(--line);
          }
          .document-icon {
            display: grid;
            place-items: center;
            width: 74px;
            height: 88px;
            border-radius: 12px;
            color: #fff;
            background: linear-gradient(145deg, var(--green-800), var(--slate-900));
            font-weight: 950;
            letter-spacing: 0.08em;
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16);
          }
          .document-tile strong,
          .document-tile span {
            display: block;
            overflow-wrap: anywhere;
          }
          .document-tile span {
            margin-top: 7px;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.45;
          }
          .timeline {
            position: relative;
            display: grid;
            gap: 8px;
          }
          .timeline-item {
            display: grid;
            grid-template-columns: 18px minmax(0, 1fr) auto;
            gap: 10px;
            align-items: center;
            padding: 11px;
            border-radius: 16px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .timeline-item.ok,
          .timeline-item.ready {
            border-color: rgba(34,201,139,0.28);
            background: linear-gradient(90deg, rgba(236,253,245,0.92), #fff);
          }
          .timeline-item.review,
          .timeline-item.blocked {
            border-color: rgba(239,68,68,0.24);
            background: linear-gradient(90deg, rgba(255,241,242,0.92), #fff);
          }
          .timeline-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--green-500);
            box-shadow: 0 0 0 4px rgba(34,201,139,0.12);
          }
          .timeline-item.review .timeline-dot,
          .timeline-item.blocked .timeline-dot {
            background: var(--red-600);
            box-shadow: 0 0 0 4px rgba(220,38,38,0.11);
          }
          .timeline-item.pending .timeline-dot {
            background: var(--blue-700);
            box-shadow: 0 0 0 4px rgba(29,78,216,0.10);
          }
          .timeline-item strong {
            display: block;
            color: var(--ink);
            font-size: 13px;
          }
          .timeline-item p {
            margin: 4px 0 0;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .tool-grid,
          .mini-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin: 10px 0 12px;
          }
          .tool-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
          .tool-badge {
            position: relative;
            padding-top: 13px;
            border-top: 4px solid var(--slate-200);
          }
          .tool-badge.ok {
            border-top-color: var(--green-500);
            background: var(--green-50);
          }
          .tool-badge.blocked {
            border-top-color: var(--red-600);
            background: var(--red-50);
          }
          .tool-badge.skipped {
            border-top-color: var(--slate-500);
            background: var(--slate-50);
          }
          .tool-call-summary {
            margin-top: 8px;
            padding: 12px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--slate-50);
          }
          .tool-call-summary h4 {
            margin: 0 0 8px;
            color: var(--ink);
            font-size: 13px;
          }
          .tool-call-summary p {
            margin: -4px 0 10px;
            color: var(--muted);
            font-size: 12px;
          }
          .tool-call-summary ol {
            margin: 0;
            padding: 0;
          }
          .tool-call-list {
            display: grid;
            gap: 8px;
            list-style: none;
          }
          .tool-call-item {
            margin: 0;
            padding: 10px 11px;
            border: 1px solid var(--line);
            border-left: 4px solid var(--slate-400);
            border-radius: 12px;
            background: #fff;
            color: var(--muted);
            font-size: 13px;
          }
          .tool-call-item.executed {
            border-left-color: var(--green-500);
          }
          .tool-call-item.error {
            border-left-color: var(--red-600);
            background: var(--red-50);
          }
          .tool-call-flow {
            display: flex;
            gap: 8px;
            align-items: center;
            justify-content: space-between;
          }
          .tool-call-name {
            color: var(--ink);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            overflow-wrap: anywhere;
          }
          .tool-call-flow strong {
            color: var(--green-800);
            font-weight: 900;
            white-space: nowrap;
          }
          .tool-call-meta {
            display: grid;
            gap: 3px;
            margin-top: 7px;
            line-height: 1.35;
          }
          .tool-call-error {
            color: var(--red-700);
            font-weight: 900;
          }
          .card {
            margin-bottom: 10px;
            padding: 13px;
            border-radius: 16px;
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .primary-output {
            background:
              linear-gradient(135deg, rgba(236,253,245,0.90), rgba(255,255,255,0.96));
          }
          .decision-pair {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0;
          }
          .decision-pair div {
            border-radius: 14px;
            padding: 13px;
            background: linear-gradient(145deg, #063d31, #0f172a);
            color: #fff;
          }
          .decision-pair span {
            display: block;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 900;
            letter-spacing: 0.07em;
          }
          .decision-pair strong {
            display: block;
            margin-top: 7px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 24px;
          }
          .reason-box {
            border-radius: 14px;
            padding: 12px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .reason-box h4 {
            margin: 0 0 8px;
          }
          .reason-box p,
          .reason-box li,
          .note-list li {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .chip {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            border-radius: 999px;
            padding: 6px 10px;
            background: var(--green-50);
            border: 1px solid rgba(34,201,139,0.22);
            color: var(--green-800);
            font-size: 12px;
            font-weight: 850;
            white-space: nowrap;
          }
          .chip.blue { color: var(--blue-700); background: var(--blue-50); border-color: rgba(59,130,246,0.22); }
          .chip.purple { color: var(--purple-700); background: var(--purple-50); border-color: rgba(139,92,246,0.22); }
          .chip.red { color: var(--red-600); background: var(--red-50); border-color: rgba(239,68,68,0.22); }
          .chip.success,
          .chip.green { color: var(--green-800); background: var(--green-50); }
          .table-wrap {
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: #fff;
          }
          .heatmap-wrap {
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: #fff;
          }
          .heatmap-grid {
            display: grid;
            min-width: 760px;
          }
          .heatmap-corner,
          .heatmap-head,
          .heatmap-truck,
          .heat-cell {
            min-height: 54px;
            padding: 10px;
            border-right: 1px solid rgba(16,35,29,0.07);
            border-bottom: 1px solid rgba(16,35,29,0.07);
          }
          .heatmap-corner,
          .heatmap-head {
            display: grid;
            align-items: center;
            background: var(--slate-50);
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .heatmap-truck {
            display: grid;
            align-items: center;
            color: var(--ink);
            background: #fff;
            font-size: 13px;
            font-weight: 950;
          }
          .heat-cell {
            display: grid;
            place-items: center;
            text-align: center;
            font-size: 12px;
            font-weight: 950;
            line-height: 1.25;
            overflow-wrap: anywhere;
          }
          .heat-cell.eligible {
            color: var(--green-800);
            background: var(--green-50);
          }
          .heat-cell.blocked {
            color: var(--red-600);
            background: var(--red-50);
          }
          .heat-cell.selected {
            color: var(--green-900);
            background: linear-gradient(145deg, var(--green-100), var(--pequi-50));
            box-shadow: inset 0 0 0 2px rgba(34,201,139,0.35);
          }
          .heat-cell.empty {
            color: var(--slate-500);
            background: var(--slate-50);
          }
          .heatmap-empty {
            padding: 14px;
            border-radius: 16px;
            color: var(--muted);
            background: var(--slate-50);
            border: 1px solid var(--line);
            font-size: 13px;
          }
          table {
            width: 100%;
            min-width: 720px;
            border-collapse: collapse;
            font-size: 13px;
          }
          th {
            text-align: left;
            padding: 12px;
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            border-bottom: 1px solid var(--line);
            background: var(--slate-50);
          }
          td {
            padding: 12px;
            border-bottom: 1px solid rgba(16,35,29,0.07);
            vertical-align: middle;
          }
          tr:last-child td {
            border-bottom: 0;
          }
          tr.selected {
            background: linear-gradient(90deg, rgba(34,201,139,0.12), rgba(245,197,66,0.06));
          }
          .field-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin: 8px 0 12px;
          }
          .field-cloud span {
            border-radius: 999px;
            padding: 6px 9px;
            background: var(--green-50);
            color: var(--green-800);
            font-size: 11px;
            font-weight: 850;
          }
          .json-preview {
            border-radius: 16px;
            padding: 14px;
            background: #09231c;
            color: #c8ffe9;
            font-size: 12px;
            line-height: 1.55;
            overflow: auto;
            white-space: pre-wrap;
          }
          .streamlit-card {
            padding-bottom: 4px;
          }
          .audit-list {
            display: grid;
            gap: 10px;
          }
          .audit-step {
            display: grid;
            grid-template-columns: 120px minmax(0, 1fr);
            gap: 10px;
            align-items: start;
          }
          .audit-step strong {
            color: var(--green-800);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .audit-step span {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.4;
            overflow-wrap: anywhere;
          }
          .phone-card {
            display: grid;
            place-items: center;
          }
          .phone {
            width: min(320px, 100%);
            border-radius: 30px;
            padding: 12px;
            background: #111827;
            box-shadow: 0 30px 60px rgba(15,23,42,0.24);
          }
          .phone-head {
            padding: 15px;
            border-radius: 22px 22px 8px 8px;
            color: #fff;
            background: linear-gradient(145deg, var(--green-500), var(--green-800));
          }
          .phone-head strong,
          .phone-head span {
            display: block;
          }
          .phone-head span {
            margin-top: 3px;
            color: rgba(255,255,255,0.70);
            font-size: 12px;
          }
          .bubble {
            margin-top: 10px;
            border-radius: 16px;
            padding: 11px 12px;
            background: #fff;
            font-size: 12px;
            line-height: 1.45;
          }
          .bubble.me {
            background: #d9fdd3;
          }
          .phone-input {
            margin-top: 10px;
            border-radius: 999px;
            padding: 10px 13px;
            background: rgba(255,255,255,0.86);
            color: #8a8a8a;
            font-size: 12px;
          }
          .error-card {
            padding: 16px;
            border-radius: 18px;
            background: var(--red-50);
            color: var(--red-600);
            border: 1px solid rgba(239,68,68,0.22);
          }
          @media (max-width: 1280px) {
            .status-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            .hero { grid-template-columns: 1fr; }
            .decision-story { grid-template-columns: 1fr; }
            .tool-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          }
          @media (max-width: 860px) {
            .status-grid,
            .hero-proof,
            .story-grid,
            .decision-pair,
            .input-summary,
            .package-grid,
            .tool-grid,
            .mini-metrics {
              grid-template-columns: 1fr;
            }
            .run-strip,
            .section-title,
            .card-head {
              flex-direction: column;
            }
            .timeline-item {
              grid-template-columns: 18px minmax(0, 1fr);
            }
            .queue-card {
              grid-template-columns: 48px minmax(0, 1fr);
            }
            .queue-state,
            .queue-after {
              grid-column: 2;
              justify-self: start;
            }
            .timeline-item .chip {
              grid-column: 2;
              width: fit-content;
            }
            .hero h1 {
              font-size: 28px;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
