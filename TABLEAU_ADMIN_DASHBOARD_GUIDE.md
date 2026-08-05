# Tableau Admin Dashboard - Complete Feature Guide

## Overview

The **Tableau Admin Dashboard** is an administrative tool that provides visibility into Tableau Server content, permissions, users, and system health. It helps administrators monitor workbooks, datasources, custom views, and user permissions across multiple Tableau sites.

---

## Key Features & Sections

### 1. **Overview**
**Purpose:** Dashboard summary and quick statistics

**What you see:**
- High-level metrics about your Tableau environment
- Total workbooks, datasources, and users count
- System status indicators

---

### 2. **Workbooks**
**Purpose:** Manage and monitor all Tableau workbooks

**Key Terms:**
- **Workbook**: A Tableau file containing dashboards, views, and data visualizations
- **Owner**: The user who created or owns the workbook
- **Project**: Organizational folder/container for grouping related workbooks
- **Extract Status**: Whether the workbook's data is live-connected or extracted (cached)
- **Last Updated**: When the workbook was last modified
- **Stale**: A workbook that hasn't been updated in a long time (>90 days by default)

**What you can do:**
- View all workbooks in your Tableau environment
- Filter by project, owner, or status
- Check extract refresh status
- Identify underutilized workbooks

---

### 3. **Data Sources**
**Purpose:** Monitor datasources that feed data into workbooks

**Key Terms:**
- **Datasource**: The data connection/query that provides data to workbooks
- **Published Datasource**: A reusable datasource that multiple workbooks can connect to
- **Extract**: A snapshot of data cached on Tableau Server (faster, but not real-time)
- **Live Connection**: Real-time connection to the source database
- **Owner**: Person responsible for maintaining the datasource
- **Project**: Organizational grouping for datasources

**What you can do:**
- Monitor all datasources and their refresh status
- Check which workbooks depend on each datasource
- Identify stale or failing datasources
- Track datasource ownership

---

### 4. **Users**
**Purpose:** Manage and monitor Tableau user accounts

**Key Terms:**
- **Site Role**: User's permission level on Tableau Server:
  - **Admin**: Full administrative access
  - **Creator**: Can create and edit content
  - **Explorer**: Can view and interact with content
  - **Viewer**: View-only access
- **Last Login**: When the user last accessed Tableau Server
- **Account Number**: Internal employee/organization ID (synced from BigQuery)

**What you can do:**
- View all users across sites
- Check last login dates to identify inactive users
- Manage user permissions
- View associated account numbers

---

### 5. **Permissions**
**Purpose:** Manage who has access to what content

**Key Terms:**
- **Permission Grant**: A rule defining what a user/group can do with a workbook/datasource
- **Allowed**: Permission is granted (checkmark)
- **Denied**: Permission is explicitly blocked (X)
- **Unset**: No explicit permission (uses default rules)

**Permission Types:**
- **View**: Can view the content
- **Filter**: Can interact with dashboard filters
- **Download**: Can export/download data
- **Share**: Can share with other users
- **Edit**: Can modify the content

**What you can do:**
- See all permission rules in your environment
- Identify overly permissive access
- Find who has access to specific content
- Audit security and compliance

---

### 6. **Lineage**
**Purpose:** Understand data flow and dependencies

**Key Terms:**
- **Lineage**: The path data takes from source database → Datasource → Workbook → Dashboard
- **Upstream**: The sources/dependencies that feed into a workbook
- **Downstream**: The workbooks/dashboards that depend on a datasource

**What you can do:**
- Trace data lineage from database to dashboard
- Understand dependencies between objects
- Plan maintenance (when updating a datasource, see what breaks)
- Impact analysis

---

### 7. **Custom Views**
**Purpose:** Monitor saved views created by individual users

**Key Terms:**
- **Custom View**: A personalized version of a worksheet that a user saved with specific filters/selections
- **Shared**: Visible to anyone with access to the parent workbook
- **Private**: Only visible to the owner
- **Owner Email**: Email address of the user who created the custom view
- **Account #**: Employee/organization ID associated with the owner (synced from BigQuery)
- **Base View**: The original worksheet/dashboard the custom view is based on

**Filters:**
- **All workbooks / Specific workbook**: Filter by which workbook contains the view
- **All base views / Specific view**: Filter by the parent worksheet/dashboard
- **All owners / Specific owner**: Filter by who created the view
- **Shared or private**: Show only shared views, private views, or all
- **Mayo only / Non-Mayo only**: Filter by email domain (@mayo.edu vs external)

**What you can do:**
- Track custom views created by users
- See who created what
- Filter by Mayo vs non-Mayo (external) users
- View associated account numbers for user identification
- Monitor sharing practices
- Export custom view inventory

---

### 8. **Subscriptions**
**Purpose:** Monitor scheduled email subscriptions

**Key Terms:**
- **Subscription**: Automatic emailing of a view/dashboard to users on a schedule
- **Frequency**: How often the email is sent (daily, weekly, monthly)
- **Recipient**: Who receives the subscription emails

**What you can do:**
- See all active subscriptions
- Identify which content is frequently emailed
- Find subscriptions with delivery issues
- Track subscription usage

---

### 9. **Webhooks**
**Purpose:** Track real-time event notifications

**Key Terms:**
- **Webhook**: Automated notification when a specific event occurs (workbook published, user login, etc.)
- **Event**: The trigger (e.g., "datasource refreshed failed")
- **Endpoint**: Where the notification is sent (URL, Slack, Teams, etc.)

**What you can do:**
- Monitor all configured webhooks
- Check webhook delivery status
- Track real-time events in your Tableau environment
- Integrate with alerting systems

---

### 10. **Refresh Health**
**Purpose:** Monitor datasource extract refresh success/failure

**Key Terms:**
- **Extract Refresh**: Process of updating cached data on Tableau Server
- **Status**: Success, Failed, In Progress
- **Frequency**: How often the extract updates (hourly, daily, weekly)
- **Last Run**: When the last refresh occurred
- **Consecutive Failures**: Number of refresh failures in a row (indicates a problem)

**What you can do:**
- Monitor extract refresh jobs
- Identify failing refreshes
- Check refresh schedules
- Plan maintenance windows
- Set up alerts for failures

---

### 11. **Findings**
**Purpose:** Display audit/compliance findings and governance issues

**Key Terms:**
- **Finding**: An identified issue or concern (e.g., overly permissive access, stale content)
- **Severity**: How critical the issue is (Critical, High, Medium, Low)
- **Category**: Type of issue (Security, Performance, Governance, etc.)

**What you can do:**
- See system-identified issues
- Prioritize remediation efforts
- Track compliance concerns
- Monitor governance

---

### 12. **Health**
**Purpose:** System health and status overview

**What you can see:**
- Server uptime/status
- Refresh job health
- Connectivity issues
- Performance metrics

---

## Account Numbers Feature

### What is it?
The Account Numbers feature enriches the Custom Views data with employee/organization IDs from your BigQuery database, making it easier to identify users.

### How it works:
1. **Data Source**: Mayo Clinic's BigQuery table containing employee account mappings
2. **Sync Process**: Automatically matches user emails between Tableau and BigQuery
3. **Display**: Shows account numbers in the "Account #" column in Custom Views

### Example:
```
Owner Email              | Account #
shore.robin@mayo.edu     | 7025981
vkeyi@vhchealth.org      | - (not found in BigQuery)
lahner.carrie@mayo.edu   | 7022467
```

### Filtering by Account Type:
- **Mayo only**: Shows views owned by @mayo.edu accounts (likely to have account numbers)
- **Non-Mayo only**: Shows views owned by external accounts (likely won't have account numbers)

---

## Common Workflows

### 1. **Find Stale Content**
1. Go to **Workbooks**
2. Look for workbooks not updated recently
3. Consider archiving or updating them

### 2. **Audit User Permissions**
1. Go to **Permissions**
2. Filter for specific users/workbooks
3. Identify overly permissive access
4. Adjust as needed

### 3. **Troubleshoot Data Issues**
1. Go to **Lineage**
2. Trace the data path from source to dashboard
3. Check **Refresh Health** for datasource failures
4. Review **Findings** for identified issues

### 4. **Identify Users of Custom Views**
1. Go to **Custom Views**
2. Filter by **Mayo only** to see Mayo employees
3. View **Owner Email** and **Account #** to identify users
4. Use account numbers to correlate with HR systems

### 5. **Monitor Extract Refreshes**
1. Go to **Refresh Health**
2. Check for consecutive failures
3. Review **Findings** for failure alerts
4. Investigate datasource connections

---

## Key Metrics to Monitor

| Metric | What It Means | Action if Concerning |
|--------|---------------|----------------------|
| Stale Workbooks | Content not updated in 90+ days | Review, update, or archive |
| Failed Extracts | Datasource refresh failed | Check datasource connection, investigate error |
| Overly Permissive Permissions | Too many users have access | Audit and restrict access |
| Inactive Users | No login in 90+ days | Consider removing or checking with user |
| Unused Datasources | Not connected to any workbooks | Consider archiving |
| High Subscription Count | Many scheduled emails | Review frequency, consolidate if possible |

---

## Support & Questions

For questions about:
- **Specific workbooks/content**: Check the Owner email and contact them
- **Permissions/access**: Contact your Tableau admin
- **Data quality issues**: Check Lineage and Refresh Health; investigate data source
- **System issues**: Review Health section or contact IT support

---

## Tips for Best Practices

1. **Regular Reviews**: Check the dashboard weekly to catch issues early
2. **Governance**: Use Findings to track compliance and governance items
3. **Communication**: Share findings with workbook owners for collaboration
4. **Documentation**: Keep track of critical workbooks and dependencies
5. **Cleanup**: Archive old/unused content to maintain performance
6. **Monitoring**: Set up alerts for extract failures and permission changes

---

**Last Updated**: 2026-08-05
**Dashboard Version**: 1.0
