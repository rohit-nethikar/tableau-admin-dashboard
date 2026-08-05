# Dashboard Features Overview

The Tableau Admin Dashboard is organized into 12 main sections, each serving a specific purpose in managing your Tableau environment.

## Feature Categories

### Content Management
- [Workbooks](#workbooks) - Manage and monitor dashboards
- [Data Sources](#data-sources) - Track datasource health
- [Lineage](#lineage) - Understand data dependencies

### User & Access Management
- [Users](#users) - Manage user accounts
- [Permissions](#permissions) - Audit access control
- [Custom Views](#custom-views) - Monitor saved user views

### System Monitoring
- [Overview](#overview) - Dashboard summary
- [Health](#health) - System status
- [Refresh Health](#refresh-health) - Extract refresh monitoring
- [Findings](#findings) - Governance issues
- [Subscriptions](#subscriptions) - Email subscriptions
- [Webhooks](#webhooks) - Real-time notifications

---

## Workbooks

**Purpose:** Manage and monitor all Tableau workbooks

### Key Information
- Workbook name and owner
- Project assignment
- Extract status (live or cached)
- Last update time
- Staleness indicator

### What You Can Do
✅ View all workbooks across sites  
✅ Filter by project, owner, or status  
✅ Check extract refresh status  
✅ Identify underutilized workbooks  
✅ Track workbook ownership  
✅ Monitor update frequency  

### Key Terms
- **Workbook**: Tableau file containing dashboards and visualizations
- **Project**: Organizational folder for grouping workbooks
- **Extract Status**: Whether data is live-connected or cached on server
- **Stale**: Workbook not updated in 90+ days (configurable)
- **Owner**: User who created/owns the workbook

---

## Data Sources

**Purpose:** Monitor datasources that feed data into workbooks

### Key Information
- Datasource name and owner
- Project assignment
- Connection type (live or extract)
- Refresh status
- Last refresh time
- Dependencies

### What You Can Do
✅ Monitor all datasources  
✅ Check refresh status  
✅ Identify data refresh failures  
✅ See which workbooks use each datasource  
✅ Track datasource ownership  
✅ Plan maintenance windows  

### Key Terms
- **Datasource**: Data connection/query providing data to workbooks
- **Extract**: Snapshot of data cached on Tableau Server
- **Live Connection**: Real-time connection to source database
- **Refresh**: Process of updating extracted data
- **Published Datasource**: Reusable datasource for multiple workbooks

---

## Users

**Purpose:** Manage and monitor Tableau user accounts

### Key Information
- User name and email
- Site role (Admin, Creator, Explorer, Viewer)
- Last login date
- Account number (from BigQuery)
- Associated sites

### What You Can Do
✅ View all users across sites  
✅ Check last login dates  
✅ Identify inactive users  
✅ Manage user permissions  
✅ View employee account numbers  
✅ Audit user activity  

### Key Terms
- **Site Role**: Permission level on Tableau Server
  - **Admin**: Full administrative access
  - **Creator**: Can create and edit content
  - **Explorer**: Can interact with content
  - **Viewer**: View-only access
- **Account Number**: Employee/organization ID
- **Last Login**: When user last accessed Tableau

---

## Permissions

**Purpose:** Audit and manage who has access to what

### Key Information
- Permission rules for each object
- User/group and object combinations
- Allowed/denied/unset permissions
- Permission types (view, edit, filter, download, share)

### What You Can Do
✅ See all permission rules  
✅ Identify overly permissive access  
✅ Find who has access to specific content  
✅ Audit security compliance  
✅ Plan permission changes  

### Key Terms
- **Permission Grant**: A rule defining access
- **Allowed**: Permission granted (✓)
- **Denied**: Permission blocked (✗)
- **Unset**: Uses default rules
- **Permission Types**: View, Filter, Download, Share, Edit

---

## Custom Views

**Purpose:** Monitor saved views created by users

### Key Information
- View name and owner
- Parent workbook and worksheet
- Owner email and account number
- Shared or private
- Creation date

### What You Can Do
✅ Track all custom views  
✅ See view creators and owners  
✅ Filter by Mayo (@mayo.edu) vs external accounts  
✅ View associated employee account numbers  
✅ Understand sharing practices  
✅ Export view inventory  

### Filters Available
- By workbook
- By base view (parent worksheet)
- By owner
- By sharing status
- **By account type** (Mayo only / Non-Mayo only)

### Key Terms
- **Custom View**: User's saved filter/selection on a worksheet
- **Shared**: Visible to anyone with workbook access
- **Private**: Only visible to owner
- **Base View**: The original worksheet the view is based on
- **Account #**: Employee ID synced from BigQuery

---

## Lineage

**Purpose:** Understand data flow and dependencies

### Key Information
- Data source to workbook connections
- Dependencies between objects
- Impact relationships

### What You Can Do
✅ Trace data lineage  
✅ Understand dependencies  
✅ Plan maintenance impact  
✅ Perform impact analysis  
✅ Find data quality issues  

### Key Terms
- **Lineage**: Data path from source database → datasource → workbook → dashboard
- **Upstream**: Data sources that feed into a workbook
- **Downstream**: Workbooks depending on a datasource

---

## Overview

**Purpose:** Dashboard summary and quick statistics

### What You See
- High-level metrics
- System status indicators
- Key statistics and trends
- Quick access to other sections

---

## Health

**Purpose:** Monitor system health and status

### What You See
- Server uptime/status
- Refresh job health
- Connectivity issues
- Performance metrics
- System alerts

---

## Refresh Health

**Purpose:** Monitor datasource extract refresh success/failure

### Key Information
- Extract refresh jobs
- Success/failure status
- Refresh frequency
- Last run time
- Consecutive failure count

### What You Can Do
✅ Monitor refresh jobs  
✅ Identify failing refreshes  
✅ Check refresh schedules  
✅ Plan maintenance  
✅ Set up alerts  

### Key Terms
- **Extract Refresh**: Process of updating cached data
- **Consecutive Failures**: Number of failures in a row (indicates problem)
- **Frequency**: How often refresh runs

---

## Findings

**Purpose:** Display audit findings and governance issues

### What You See
- Identified issues and concerns
- Issue severity
- Issue category (Security, Performance, Governance)
- Recommendations

### What You Can Do
✅ See identified issues  
✅ Prioritize remediation  
✅ Track compliance  
✅ Monitor governance  

---

## Subscriptions

**Purpose:** Monitor scheduled email subscriptions

### Key Information
- Subscription target (view/dashboard)
- Recipients
- Schedule/frequency
- Status

### What You Can Do
✅ See all subscriptions  
✅ Identify frequently emailed content  
✅ Find delivery issues  
✅ Track subscription usage  

---

## Webhooks

**Purpose:** Track real-time event notifications

### Key Information
- Webhook events
- Notification endpoints
- Event types
- Delivery status

### What You Can Do
✅ Monitor configured webhooks  
✅ Check delivery status  
✅ Track real-time events  
✅ Integrate with alerting systems  

---

## Next Steps

- **Get started:** [Getting Started Guide](../guides/getting-started.md)
- **Learn workflows:** [Common Workflows](../guides/workflows.md)
- **Best practices:** [Best Practices](../guides/best-practices.md)
- **Account numbers:** [Account Numbers Guide](../account-numbers/overview.md)
