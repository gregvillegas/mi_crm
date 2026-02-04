# Executive CRM Dashboard

## Overview
The Executive CRM Dashboard provides a comprehensive, high-level view of sales performance designed specifically for VP and executive-level users. It consolidates key metrics from across the organization into five strategic components.

## Features

### 1. Team Performance KPI Cards (Top-Level)
- **Monthly Revenue**: Current month revenue with growth percentage vs. previous month
- **Deals Closed**: Number of deals closed this month with growth comparison
- **Secondary KPIs**: Total pipeline value, active deals count, and average deal size

### 2. Group Performance Chart (Middle-Level)
- **Horizontal Bar Chart**: Visualizes revenue and pipeline value by sales group
- **Comparative Analysis**: Shows closed revenue vs. active pipeline value
- **Group Types**: Includes both regular groups and Technical Sales Groups (TSG)

### 3. Sales Funnel Overview
- **Three Pipeline Stages**:
  - Newly Quoted (Pink)
  - Closable This Month (Yellow) 
  - Project Based (Green)
- **Stage Metrics**: Deal count, total value, and percentage of pipeline
- **Aging Indicators**: 
  - Green: < 14 days (healthy)
  - Yellow: 14-30 days (monitor)
  - Red: > 30 days (needs attention)

### 4. Individual Performance Table (Bottom-Level)
- **Sortable & Filterable**: DataTables integration for easy analysis
- **Key Metrics**:
  - Total Revenue
  - Pipeline Value
  - Active/Won Deals
  - Activity Completion Rate
  - Average Deal Size
- **Performance Rankings**: Top performers highlighted with badges
- **Performance Categories**:
  - Excellent: > ₱500,000 revenue
  - Good: ₱200,000 - ₱500,000
  - Average: ₱50,000 - ₱200,000
  - Needs Attention: < ₱50,000

### 5. Quick Insights Panel
- **Automated Insights**: AI-driven recommendations based on performance data
- **Insight Types**:
  - Revenue Growth Alerts
  - Pipeline Coverage Warnings
  - Funnel Aging Notifications
  - Performance Gap Identification
  - Group Performance Disparities
- **Actionable Recommendations**: Specific next steps for each insight

## Access Control
- **Restricted Access**: Only VP, GM, President, and Admin roles can access
- **Navigation**: Available in Monitoring dropdown menu with crown icon
- **URL**: `/sales-monitoring/executive/`

## Technical Implementation

### Backend (Django)
- **View**: `executive_dashboard()` in `sales_monitoring/views.py`
- **Data Aggregation**: `get_executive_dashboard_data()` function
- **Insights Engine**: `generate_executive_insights()` function
- **Models Used**: SalesFunnel, SalesActivity, Teams, Groups, Users

### Frontend (HTML/CSS/JS)
- **Template**: `sales_monitoring/templates/sales_monitoring/executive_dashboard.html`
- **Charts**: Chart.js for horizontal bar chart
- **Tables**: DataTables for sortable performance table
- **Styling**: Bootstrap 5 with custom CSS gradients and animations
- **Responsive**: Mobile-friendly design

### Data Sources
- **Sales Funnel**: Revenue, pipeline value, deal stages
- **Activities**: Completion rates, activity counts
- **Teams/Groups**: Organizational structure and assignments
- **Time Periods**: Current month vs. previous month comparisons

## Sample Data
Use the included sample data script to populate test data:

```bash
cd /home/greg/projects/crm_project
python create_sample_data.py
```

**Test Accounts:**
- VP: `vp_john` / `password123`
- AVP: `avp_alice` / `password123`
- Supervisor: `sup_carol` / `password123`
- Salesperson: `sales_emma` / `password123`

## Key Features

### Real-time Updates
- Auto-refresh every 5 minutes
- Live timestamp showing last update
- Dynamic data calculations

### Interactive Elements
- Clickable insight cards
- Sortable performance table
- Filterable salesperson data
- Responsive chart interactions

### Performance Optimization
- Efficient database queries with select_related
- Paginated data where appropriate
- Optimized JavaScript libraries (CDN)

## Usage Instructions

1. **Login** with VP or executive-level account
2. **Navigate** to Monitoring → Executive Dashboard
3. **Review KPIs** in the top performance cards
4. **Analyze Groups** using the horizontal bar chart
5. **Monitor Pipeline** stages and aging indicators
6. **Identify** top/bottom performers in the table
7. **Act** on automated insights and recommendations

## Customization Options

### Adding New Insights
Edit the `generate_executive_insights()` function to add custom business rules and thresholds.

### Modifying KPIs
Update the `get_executive_dashboard_data()` function to include additional metrics or change calculation methods.

### Styling Changes
Modify the CSS in the template or add custom styles in the `extra_css` block.

## Performance Considerations
- Dashboard loads all data server-side for immediate display
- Chart data is JSON-serialized for JavaScript consumption
- Database queries are optimized with proper indexing
- Auto-refresh prevents stale data issues

## Future Enhancements
- Export dashboard data to PDF/Excel
- Drill-down capabilities for detailed analysis
- Custom date range selection
- Real-time notifications for critical insights
- Integration with external BI tools

## Support
For technical support or feature requests, contact the development team.
