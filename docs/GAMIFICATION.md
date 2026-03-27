# Gamification System – Executive & AVP Guide

This document explains how the CRM’s Gamification module works, why it motivates salespeople, and how Executives/AVPs can leverage it to drive behavior and performance.

---

## Overview
- Purpose: Encourage the right sales behaviors through points, levels, badges, streaks, and daily missions.
- Visibility: Leaderboards and badges are visible to users for recognition and healthy competition.
- Integration: Points are awarded automatically when normal sales activities happen (creating leads/proposals, winning deals, sending campaign emails, daily logins).

Key code locations:
- Models: [gamification/models.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/models.py)
- Signals (auto-awards): [gamification/signals.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py)
- Daily mission generator: [gamification/utils.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/utils.py)
- Leaderboard view: [gamification/views.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/views.py) and [leaderboard.html](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/templates/gamification/leaderboard.html)
- Badges view: [badges.html](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/templates/gamification/badges.html)
- Status in UI (points/level/streak): [gamification/context_processors.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/context_processors.py)

---

## Core Concepts
- Points: Quantify user actions; accumulate over time.
- Levels: Reflect long-term progress; Level = 1 + floor(total_points / 1000).
- Streaks: Count consecutive active days with point-awarding activity; resets if a day is missed.
- Badges: Milestone achievements (e.g., 1,000 points; 7-day streak; “Millionaire Deal”).
- Missions: Short-term goals (daily/weekly) with bonus points on completion.

---

## Points – What earns them?
- Create Lead (+5): Awarded via signal when a new Lead is created [lead_created](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L114-L118).
- Create Proposal (+10): Awarded via signal when a Proposal is created [proposal_created](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L119-L123).
- Deal Won (+50; +100 for ≥ PHP 1,000,000): Awarded on funnel win; also grants “Millionaire Deal” badge when applicable [deal_closed](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L128-L147).
- Daily Login (+1 per day): Awarded once per day when the user logs in [user_login_reward](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L149-L165).
- Mass Mailing (Campaign Email Sent) (+5 per recipient): Awarded by the mass mailing worker after each successful send [process_mail_queue.py](file:///Users/greg/Documents/trae_projects/mi_crm/mass_mailing/management/commands/process_mail_queue.py).

All point awards go through `award_points()` which also:
- Updates streaks and last-activity date
- Logs the event to `PointLog`
- Advances mission progress and checks badge milestones

---

## Levels
- Formula: `level = 1 + (total_points // 1000)`
- Example:
  - 0–999 pts → Level 1
  - 1000–1999 pts → Level 2
  - 2000–2999 pts → Level 3
- Implementation: [GamificationProfile.add_points](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/models.py#L17-L23)

---

## Ranks (Leaderboard)
- Leaderboard shows the Top 10 salespeople by total points [leaderboard_view](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/views.py#L6-L26).
- Individual Rank: Calculated by counting how many salespeople have more points than the current user (rank = better_scores + 1).
- UI: Includes user avatars, level badges, streak indicator, and medal icons for Top 3.

---

## Streaks
- Increment: If user’s last point-awarding activity was **yesterday**, streak increases by 1.
- Reset: If last activity was more than one day ago, streak resets to 1 on next activity day.
- Display: Shown in navbar via context processor and on Leaderboard.
- Implementation: [signals.award_points](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L35-L47)

---

## Badges
- Stored in `Badge` with `criteria_code`; earned stored in `UserBadge`.
- Built-in criteria checked:
  - `score_1000` (≥ 1000 pts)
  - `score_5000` (≥ 5000 pts)
  - `streak_7` (≥ 7-day streak)
  - `streak_30` (≥ 30-day streak)
  - `millionaire_deal` (deal value ≥ 1,000,000)
- Award flow: [check_badges](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L85-L100) and [award_badge](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L101-L110).
- Optional badge point bonuses: If a badge has `point_reward`, extra points are awarded automatically.
- UI: [badges.html](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/templates/gamification/badges.html) shows earned vs locked badges.

---

## Missions (Daily & Weekly)
- Defined in `Mission` with fields:
  - `mission_type`: daily/weekly
  - `target_action`: action code (e.g., `create_lead`, `create_proposal`, `deal_won`, `sent_campaign_email`, `daily_login`)
  - `target_count`: how many times the action should occur
  - `reward_points`: bonus points on completion
- Assignment:
  - On login, the system ensures **3 daily missions** for the user [generate_daily_missions](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/utils.py#L5-L45) and [user_login_reward](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L149-L165).
  - Missions are randomly selected from active daily missions.
  - Progress is tracked in `UserMissionProgress` and updated inside `award_points()` via [check_missions](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/signals.py#L63-L84).
- Who creates missions?
  - Executives/AVPs/Admins define the catalog of missions (title, target action, counts, rewards) in the database.
  - The CRM can expose these in Django Admin for easy management; if not visible, they can be seeded via a management command or the shell.
- Completion:
  - When `current_count` ≥ `target_count`, mission is marked completed, and bonus points are awarded immediately.

---

## How This Motivates Salespeople
- Immediate Feedback: Points, streaks, and badges provide instant recognition for desirable behaviors.
- Clear Short-Term Goals: Daily missions offer concrete targets to focus effort and build momentum.
- Healthy Competition: Leaderboards and ranks keep performance visible and encourage progress.
- Long-Term Growth: Levels and milestone badges reward sustained activity and consistent habits.
- Alignment: By choosing mission target actions strategically (e.g., create leads, follow-ups, send campaigns), management nudges the exact behaviors that lead to revenue.

---

## Executive & AVP Playbook
- Define the mission catalog aligned to strategy (e.g., “Create 5 leads”, “Send 10 follow-ups”, “Book 2 meetings”).
- Adjust rewards to emphasize high-value actions (e.g., larger bonuses for closable deals or high-quality leads).
- Monitor leaderboard weekly to identify top performers and those who need coaching.
- Use streaks to spot consistency; coach “reset” patterns to help salespeople form daily habits.
- Periodically introduce limited-time badges (e.g., “Q2 Challenger”) for campaigns or seasonal pushes.

---

## Navigation & Views
- Leaderboard: `/gamification/leaderboard/` [urls.py](file:///Users/greg/Documents/trae_projects/mi_crm/gamification/urls.py)
- Badges: `/gamification/badges/`
- Daily Missions: Displayed on the home dashboard; automatically assigned on login.

---

## Notes & Extensibility
- Admin Setup: Ensure Missions and Badges are present in the DB; consider adding Django Admin registrations for easy management.
- Duplicate Protection: Point logs can be extended to enforce strict per-object de-duplication.
- Analytics: PointLog provides a full audit trail for reporting.

This system is designed to be simple, transparent, and extensible—giving Executives and AVPs practical levers to drive the right behaviors and celebrate wins across the sales organization.
