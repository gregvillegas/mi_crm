# Sales Activity Monitoring System

This feature provides comprehensive monitoring capabilities for supervisors to track and oversee their sales team's activities including calls, meetings, emails, proposals, tasks, and other sales-related activities.

## Features Overview

### For Supervisors
- **Team Activity Dashboard**: Monitor all activities from supervised salespeople
- **Real-time Statistics**: Track completion rates, overdue activities, and pending reviews
- **Activity Review System**: Review and approve salesperson activities
- **Performance Analytics**: View individual and team performance metrics
- **Bulk Operations**: Update multiple activities at once
- **Report Generation**: Generate daily, weekly, monthly, or custom period reports
- **Export Capabilities**: Export activity data to CSV
- **Filtering**: Advanced filtering by date, status, priority, activity type, and salesperson

### For Salespeople
- **Personal Activity Dashboard**: View and manage own activities
- **Quick Activity Logging**: Fast entry for completed activities
- **Activity Management**: Create, update, and track activities
- **Calendar View**: Visual calendar interface for scheduled activities
- **Overdue Alerts**: Clear visibility of overdue activities
- **Activity History**: Track all changes and updates

## Activity Types

The system supports the following activity types:

1. **Phone Call** - Cold calls, warm calls, follow-ups, demos, support calls
2. **Meeting** - Initial meetings, demos, proposals, negotiations, closing meetings
3. **Email** - Introduction emails, follow-ups, proposals, quotes, contracts
4. **Proposal** - Creating and managing sales proposals with value tracking
5. **Task** - Research, preparation, documentation, administrative work
6. **Demo** - Product demonstrations and presentations
7. **Follow-up** - Follow-up activities after initial contact
8. **Research** - Customer and market research activities

## Key Models

### SalesActivity (Main Model)
- Basic activity information (title, description, type)
- Assignment (salesperson, customer)
- Status tracking (planned, in_progress, completed, cancelled, postponed)
- Priority levels (low, medium, high, urgent)
- Scheduling (planned and actual start/end times)
- Supervisor review fields
- Follow-up requirements

### Activity-Specific Details
- **CallActivity**: Phone number, call type, outcomes
- **MeetingActivity**: Meeting type, location, attendees, outcomes
- **EmailActivity**: Subject, recipients, tracking (opened/responded)
- **ProposalActivity**: Value, currency, status, win probability
- **TaskActivity**: Category, estimated/actual hours

### Monitoring Features
- **ActivityLog**: Comprehensive audit trail of all changes
- **SupervisorReport**: Generated reports with metrics and analytics
- **ActivityReminder**: Automated reminders for overdue or upcoming activities

## Usage Instructions

### Setting Up Activity Monitoring

1. **Add Activity Types** (if not using defaults):
   ```bash
   python manage.py populate_activity_types
   ```

2. **Access the System**:
   - Supervisors: Navigate to `/sales-monitoring/` for main dashboard
   - Salespeople: Access personal dashboard at `/sales-monitoring/`

### For Supervisors

#### Monitoring Team Activities
1. Go to Sales Activity Monitoring dashboard
2. View real-time statistics and metrics
3. Use filters to narrow down activities by:
   - Date range
   - Status (planned, in_progress, completed, etc.)
   - Priority level
   - Activity type
   - Specific salesperson
   - Review status
   - Overdue activities only

#### Reviewing Activities
1. Click on any activity to view details
2. Add supervisor notes
3. Mark as reviewed to track oversight
4. All reviews are logged in audit trail

#### Bulk Operations
1. Use "Bulk Update" button from dashboard
2. Select multiple activities
3. Apply status changes or mark as reviewed
4. Add batch supervisor notes

#### Generating Reports
1. Go to Reports section
2. Choose report type (daily, weekly, monthly, custom)
3. Select date range for custom reports
4. Generate comprehensive performance reports
5. Export reports or activity data to CSV

#### Team Performance View
- View individual salesperson metrics
- Compare completion rates across team
- Identify top performers and those needing support
- Track activity trends over time

### For Salespeople

#### Logging Activities
1. **Quick Log**: Use for immediate activity recording
2. **Full Form**: Create detailed activities with scheduling
3. **Update Status**: Mark activities as completed with actual times
4. **Add Notes**: Document outcomes and next steps

#### Managing Your Activities
1. View today's scheduled activities
2. See upcoming activities for the week
3. Address overdue activities immediately
4. Track your completion rates and performance

#### Activity Details
- Each activity can have specific details based on type
- Call activities: track outcomes and next steps
- Meetings: record attendees and results
- Emails: track open rates and responses
- Proposals: monitor value and win probability

## Key Benefits

### For Management
- **Visibility**: Complete oversight of sales team activities
- **Accountability**: Clear tracking of salesperson productivity
- **Performance Metrics**: Data-driven insights into team performance
- **Compliance**: Audit trail for all sales activities
- **Reporting**: Automated report generation for various periods

### For Sales Teams
- **Organization**: Better activity planning and time management
- **Follow-up Management**: Never miss important follow-ups
- **Performance Tracking**: Clear view of personal productivity
- **Customer Relationship**: Better customer interaction tracking
- **Goal Achievement**: Track progress towards activity goals

## Database Structure

The system uses the following key relationships:
- Activities are linked to Users (salespeople) and Customers
- Supervisors can access activities from their managed groups
- All changes are logged in ActivityLog for audit purposes
- Activity-specific details are stored in separate models with OneToOne relationships

## Security & Permissions

- **Role-based Access**: Different dashboards and permissions by role
- **Data Isolation**: Salespeople see only their activities
- **Supervisor Scope**: Supervisors see only their team's activities
- **Admin Access**: Full system access for administrators
- **Audit Trail**: Complete logging of all changes and access

## API Endpoints

All views are accessible through the following URL patterns:
- `/sales-monitoring/` - Main dashboard (role-based routing)
- `/sales-monitoring/supervisor/` - Supervisor dashboard
- `/sales-monitoring/activity/create/` - Create new activity
- `/sales-monitoring/activity/<id>/` - Activity details
- `/sales-monitoring/reports/` - Report generation
- `/sales-monitoring/team-performance/` - Team performance metrics
- `/sales-monitoring/export/` - CSV export

## Installation and Setup

1. The app is already added to `INSTALLED_APPS` in settings
2. Migrations have been created and applied
3. Default activity types have been populated
4. Admin interface is configured

### Next Steps
1. Create some test activities to verify functionality
2. Train supervisors on using the monitoring dashboard
3. Train salespeople on activity logging
4. Set up regular report generation schedules
5. Consider adding email notifications for overdue activities

## Customization Options

### Activity Types
- Add new activity types through Django admin
- Customize icons and colors
- Set customer requirement flags

### Reports
- Customize report metrics in `SupervisorReport` model
- Add new report types
- Create automated report scheduling

### Notifications
- Extend `ActivityReminder` model for email notifications
- Add deadline warnings
- Create escalation procedures

This system provides a comprehensive foundation for sales activity monitoring that can be extended based on specific business needs.
