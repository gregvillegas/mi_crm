# Group Performance Feature for Supervisors

## Overview
This feature allows Supervisors, ASMs, and Teamleads to view their Group Performance metrics, separate from the Team Performance view which is restricted to AVPs and higher roles. Teamleads act as OIC (Officer-in-Charge) when supervisors are out and need the same access.

## What Was Implemented

### 1. New View Function (`views.py`)
- **Function**: `group_performance(request)`
- **Location**: `sales_monitoring/views.py` (line 607)
- **Access**: Restricted to users with roles `supervisor`, `asm`, or `teamlead`
- **Functionality**: 
  - Retrieves all groups managed by the logged-in supervisor/ASM (via `managed_groups`) or teamlead (via `led_groups`)
  - Generates performance data for each supervised group
  - Shows individual salesperson performance within each group
  - Calculates metrics like completion rates, overdue activities, etc.

### 2. New Template
- **File**: `sales_monitoring/templates/sales_monitoring/group_performance.html`
- **Based on**: `team_performance.html` template
- **Features**:
  - Displays group name and team affiliation
  - Shows completion rate badges (color-coded: green ≥80%, yellow ≥60%, red <60%)
  - Group summary metrics (total activities, completed, completion rate)
  - Individual performance table for all salespeople in the group
  - Empty state message when no data is available

### 3. URL Route
- **Path**: `/sales-monitoring/group-performance/`
- **Name**: `sales_monitoring:group_performance`
- **Location**: `sales_monitoring/urls.py` (line 22)

### 4. Navigation Updates

#### a. Supervisor Dashboard
- **File**: `sales_monitoring/templates/sales_monitoring/supervisor_dashboard.html` (line 14)
- **Change**: Replaced "Team Performance" button with "Group Performance" button
- **Old**: `{% url 'sales_monitoring:team_performance' %}`
- **New**: `{% url 'sales_monitoring:group_performance' %}`

#### b. Main Navigation Menu
- **File**: `templates/base.html` (line 192-194)
- **Addition**: New dropdown menu item for supervisors, ASMs, and teamleads
- **Condition**: `{% if user.role in 'supervisor,asm,teamlead' %}`
- **Link**: Group Performance menu item in the Monitoring dropdown

## Access Control

### Who Can Access Group Performance?
- ✅ **Supervisors** (`role='supervisor'`)
- ✅ **ASMs** (`role='asm'`)
- ✅ **Teamleads** (`role='teamlead'`) - Act as OIC when supervisors are out

### Who Can Access Team Performance?
- ✅ **AVPs** (`role='avp'`)
- ✅ **Admins** (`role='admin'`)
- ✅ **VPs** (`role='vp'`)
- ✅ **GMs** (`role='gm'`)
- ✅ **Presidents** (`role='president'`)

## Features & Metrics

### Group-Level Metrics
1. **Total Activities**: All activities assigned to salespeople in the group
2. **Completed Activities**: Activities with status='completed'
3. **Completion Rate**: Percentage of completed vs total activities
4. **Salespeople Count**: Number of active salespeople in the group

### Individual Salesperson Metrics
1. **Total Activities**: All activities for the salesperson
2. **Completed Activities**: Completed activities count
3. **Completion Rate**: Individual completion percentage
4. **This Week Activities**: Activities scheduled this week
5. **Overdue Activities**: Activities past deadline and not completed
6. **Performance Bar**: Visual progress indicator

## Color Coding

### Completion Rate Badges
- 🟢 **Green (Success)**: ≥ 80% completion
- 🟡 **Yellow (Warning)**: 60% - 79% completion
- 🔴 **Red (Danger)**: < 60% completion

## Navigation Flow

### For Supervisors/ASMs/Teamleads:
1. Login → Supervisor Dashboard
2. Click "Group Performance" button in top action bar
3. View their supervised/led group(s) performance
4. OR: Click "Monitoring" dropdown in main navigation
5. Select "Group Performance"

### For AVPs and Higher:
1. Login → Dashboard
2. Click "Monitoring" dropdown in main navigation
3. Select "Team Performance" (shows all groups in their teams)

## Files Modified

1. `/home/greg/all_proj/crm_project/sales_monitoring/views.py`
   - Added `group_performance()` view function

2. `/home/greg/all_proj/crm_project/sales_monitoring/urls.py`
   - Added URL route for group_performance

3. `/home/greg/all_proj/crm_project/sales_monitoring/templates/sales_monitoring/supervisor_dashboard.html`
   - Changed Team Performance button to Group Performance

4. `/home/greg/all_proj/crm_project/templates/base.html`
   - Added Group Performance menu item for supervisors/ASMs

## Files Created

1. `/home/greg/all_proj/crm_project/sales_monitoring/templates/sales_monitoring/group_performance.html`
   - New template for group performance view

## Benefits

1. **Proper Role Segregation**: Supervisors only see their groups, not all teams
2. **Focused View**: Supervisors see relevant data for their management scope
3. **Consistent Interface**: Uses same design patterns as Team Performance
4. **Security**: Permission checks ensure proper access control
5. **Clear Navigation**: Intuitive access points from dashboard and menu

## Testing Recommendations

1. ✅ Test login as Supervisor - verify access to Group Performance
2. ✅ Test login as ASM - verify access to Group Performance
3. ✅ Test login as Teamlead - verify access to Group Performance
4. ✅ Test login as Salesperson - verify NO access to Group Performance
5. ✅ Test that supervisors/teamleads only see their own groups
6. ✅ Test that teamleads see groups via `led_groups` relationship
7. ✅ Test that metrics calculate correctly
8. ✅ Test empty state when no activities exist
9. ✅ Verify navigation links work from dashboard and main menu

## Future Enhancements (Optional)

- Add date range filters for performance data
- Export group performance to CSV/PDF
- Add comparison charts between groups
- Email reports to supervisors
- Add activity type breakdown per group
