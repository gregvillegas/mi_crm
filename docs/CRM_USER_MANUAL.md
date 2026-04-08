# Micro Image CRM - User Manual

**Version:** 1.1\
**Date:** March 30, 2026\
**Prepared For:** Micro Image International Corp.

***

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Getting Started](#getting-started)
   - [System Access](#system-access)
   - [User Roles](#user-roles)
   - [Navigation](#navigation)
3. [Dashboard Overview](#dashboard-overview)
4. [Module Guides](#module-guides)
   - [Customer Management](#customer-management)
   - [Lead Generation](#lead-generation)
   - [Sales Funnel](#sales-funnel)
   - [Sales Proposals](#sales-proposals)
   - [Activity Monitoring](#activity-monitoring)
   - [Team Management](#team-management)
   - [Mass Mailing (New!)](#mass-mailing)
   - [Gamification](#gamification)
   - [Customer Service](#customer-service)
   - [File Sharing](#file-sharing)
5. [Analytics & Reporting](#analytics--reporting)
6. [Administration](#administration)

***

## Executive Summary

The **Micro Image CRM** is a comprehensive Customer Relationship Management solution designed specifically for the needs of Micro Image International Corp. It serves as a centralized platform to streamline sales operations, enhance customer engagement, and provide actionable insights through data analytics.

### Key Benefits

- **Unified Customer View**: Consolidates customer data, history, and interactions in one place.
- **Streamlined Sales Process**: From lead generation to proposal creation and deal closing, the entire workflow is digitized.
- **Data-Driven Decisions**: Real-time dashboards and analytics empower executives and managers to make informed decisions.
- **Improved Accountability**: Activity tracking and quota management ensure teams stay on target.
- **Enhanced Motivation**: Gamification features like leaderboards and badges drive performance.

***

## Getting Started

### System Access

Access the CRM via your web browser at the designated URL. Log in using your username and password.

- **Note**: Upon login, you will be greeted with a daily motivational quote to start your day!

### User Roles

The system is tailored to different roles within the organization:

- **Salesperson**: Manage own leads, customers, proposals, and activities.
- **Supervisor**: Oversee a group of salespeople, view group performance.
- **ASM (Area Sales Manager)**: Manage multiple groups/teams, set quotas.
- **AVP (Assistant Vice President)**: Strategic oversight of teams and quotas.
- **Executive (VP/GM/President)**: Full view of company performance and analytics.
- **Admin**: System configuration and user management.

### Navigation

The top navigation bar provides quick access to all major modules:

- **Dashboard**: Your personal command center.
- **Customers**: Database of all clients.
- **Leads**: Lead generation and tracking.
- **Funnel**: Sales pipeline management.
- **Proposals**: Quote generation tool.
- **Activities**: Calendar and activity logs.
- **Teams**: (For Managers) Team structure and quotas.
- **Mass Mailing**: Send personalized bulk emails to clients.
- **Files**: Document repository.

***

## Dashboard Overview

Your dashboard is personalized based on your role:

- **Salesperson**: Shows today's tasks, upcoming appointments, recent leads, and personal performance stats.
- **Manager/Executive**: Displays high-level KPIs, team performance charts, and revenue forecasts.

***

## Module Guides

### Customer Management

- **View Customers**: Browse the searchable customer database.
- **Customer 360 View**: Click on a customer to see their profile, contact persons, activity history, sales funnel, and support tickets.
- **Delinquency Tracking**: Monitor and manage delinquent accounts with color-coded status indicators.

### Lead Generation

- **Capture Leads**: Input new leads manually or import them.
- **Lead Scoring**: The system automatically scores leads based on completeness and engagement (Hot/Warm/Cold).
- **Conversion**: Convert qualified leads into customers with a single click.
- **Analytics**: View lead sources, conversion rates, and acquisition trends in the **Lead Analytics** dashboard.
- **Import Leads (CSV)**:
  - Navigate to Leads → Import.
  - Download the sample template to ensure correct columns.
  - Upload your CSV; optionally auto-calculate lead scores.
  - Role-aware defaults restrict assignment options based on your role.

### Sales Funnel

Manage your sales opportunities through distinct stages:

1. **Pink Funnel (Quoted)**: Initial proposal sent.
2. **Yellow Funnel (Closable)**: High probability of closing.
3. **Green Funnel**: Deals greater than 500K.
4. Blue Funnel: Deals below 500K

- **Pipeline View**: Drag-and-drop interface to move deals across stages.
- **Forecasting**: System calculates expected revenue based on deal probability.

### Sales Proposals

Create professional, branded PDF proposals in minutes, with multi-level approval and tighter data entry controls.

- **Create Proposal**: Select a customer, add items (products/services), and set terms.
- **Customer Filtering**: Salespeople only see customers assigned to them in the Customer dropdown.
- **Date Pickers**: Both Date and Valid until use a date picker for consistent input.
- **Items**:
  - Per-item **Warranty** field replaces Availability; shown in proposal details and the PDF items table. If an item warranty is blank, the proposal’s overall warranty is used.
  - Unit price column spacing adjusted to avoid wrapping. An Item no. column helps track entries.
  - Unit cost/price inputs use plain numeric fields without spinner arrows; values show full amounts with 2 decimals.
  - Margin% now persists between create and edit, preventing rounding shifts on reload.
  - Text Areas: Introduction, Special note, and Closing default to compact 3-line editors for cleaner forms.
  - Attachments: Upload related files on the proposal screen and choose which ones to include when emailing the client.
- **PDF Generation**: Automatically generates a standardized PDF with Micro Image branding.
- **Email Integration**: Send the proposal directly to the client from within the CRM.
  - Include selected attachments along with the generated PDF.
- **Currency Support**: Supports both PHP and USD with exchange rate handling.
- **Approvals**:
  - Proposals at or above configured PHP thresholds require approval before email sending.
  - Multi-level routing (e.g., Supervisor → ASM → AVP/GM) based on amount and team structure.
  - Supervisors/Managers use the **Approvals Inbox** to review, approve, or reject proposals.
  - Email sending is gated until the proposal is fully approved.

### Activity Monitoring

- **Log Activities**: Record calls, meetings, visits, and emails.
- **Calendar**: View your schedule and upcoming tasks.
- **Proof of Concept (POC)**: Track technical POCs and their outcomes.
- **Reports**: Generate daily or weekly activity reports for management.

### Team Management

- **Structure**: Organize users into Groups and Teams.
- **Quota Management (AVP Only)**:
  - AVPs have a dedicated "Quotas" link in the navbar.
  - Manage monthly quotas for ASMs, Supervisors, and Salespeople from a single interface.
 - **Approvals Inbox (Supervisors/Managers/Execs)**: Review proposals awaiting your approval.
 - **Approval Tiers (Exec/Admin)**:
   - Navigate to Proposals → Approval Tiers to configure thresholds and approver chains.
   - Manage tiers via UI; Import/Export CSV supported.
   - Download a ready-made CSV template or click “Seed Defaults” to populate the standard three-tier setup (500k supervisor, 1M supervisor+ASM, 3M supervisor+ASM+AVP/GM).

### Mass Mailing

The Mass Mailing module allows salespersons to send personalized bulk emails to their assigned customers while adhering to Data Privacy Act (DPA) standards and preventing spam.

- **Campaign Creation**: Create email campaigns with custom subject lines and HTML bodies.
  - **Personalization Tags**: Use `{{ contact_name }}` and `{{ company_name }}` to automatically personalize each email.
  - **Templates**: Use the "Load Template" button to quickly insert best-practice B2B sales templates (e.g., Product Updates, Quarterly Check-ins, Promotions).
- **Live Preview**: Click the "Preview" button to see exactly how the email will render in a client's inbox before sending.
- **DPA Compliance & Opt-Outs**:
  - All emails include a mandatory company footer and a secure "Unsubscribe" link.
  - If a customer unsubscribes, the system automatically adds them to an Opt-Out list and blocks them from receiving future mass mailings.
- **Rate-Limited Sending**: Once scheduled, emails are processed in the background using a rate-limited queue. This prevents server blocking and ensures high deliverability by avoiding spam filters.
- **Tracking**: Monitor the progress of your campaign in real-time on the dashboard (Total Sent, Failed, and Progress %).

### Gamification

- **Leaderboard**: See who the top performers are in real-time.
- **Badges**: Earn badges for achievements (e.g., "Top Closer", "Lead Magnet").
- **Profile**: Upload your profile picture to personalize your leaderboard appearance.

### Customer Service

- **Ticket Integration**: View "Support Tickets" directly in the Customer details page.
- **Redmine Bridge**: Seamlessly fetches ticket status and updates from the Redmine system without needing a separate login.

### File Sharing

- **Repository**: Upload and share important documents (brochures, price lists, forms).
- **Permissions**: Control who can view or download specific files.

***

## Analytics & Reporting

- **Executive Dashboard**: A bird's-eye view of the company's health, including total revenue, active deals, and team comparisons.
- **Sales Reports**: Detailed breakdown of sales performance by product, region, or salesperson.
- **Export**: Most reports can be exported to CSV/Excel for further analysis.

***

## Administration

- **User Management**: Create and manage user accounts.
- **Import Tool**: Use the `import_users` command-line tool to bulk onboard users from JSON.
  - *New*: Supports filtering by role (e.g., import only salespeople).
- **System Configuration**: Manage dropdown options, lead sources, approval tiers, and global settings.
- **Approvals Configuration**:
  - Use the **Approval Tiers** screen to adjust thresholds and chains without code changes.
  - Export the current tiers, edit offline, and import to update in bulk.

***

**Micro Image International Corp.**\
*Empowering Business through Technology*
