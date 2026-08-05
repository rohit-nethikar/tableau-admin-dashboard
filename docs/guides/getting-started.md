# Getting Started with Tableau Admin Dashboard

Welcome! This guide will walk you through the basics of using the Tableau Admin Dashboard.

## Logging In

1. **Access the Dashboard**
   - Open your browser and navigate to the dashboard URL
   - You'll see a login screen
   - Enter your Tableau Server credentials

2. **Select Your Site**
   - After login, you can switch between different Tableau sites
   - Use the site dropdown in the top navigation
   - Each site has independent data

## Dashboard Layout

### Top Navigation Bar
- **Logo/Home** - Click to go back to overview
- **Site Selector** - Switch between different Tableau sites
- **Navigation Links** - Main sections of the dashboard
- **Refresh** - Reload data from Tableau Server
- **User Menu** - Logout and settings

### Main Navigation
The left sidebar or top menu contains links to all major sections:

| Section | Purpose |
|---------|---------|
| Overview | Dashboard summary |
| Workbooks | Manage dashboards |
| Data Sources | Track datasources |
| Users | Manage accounts |
| Permissions | Audit access |
| Lineage | Understand dependencies |
| Custom Views | Monitor saved views |
| Subscriptions | Track email subscriptions |
| Webhooks | Real-time notifications |
| Health | System status |
| Findings | Governance issues |
| Refresh Health | Extract refresh status |

## Your First Task: Explore Workbooks

### Step 1: Navigate to Workbooks
1. Click **Workbooks** in the main navigation
2. You'll see a table of all workbooks in your Tableau environment

### Step 2: Understand the Columns
- **Name** - Workbook name (click to see details)
- **Project** - Where it's organized
- **Owner** - Who owns it
- **Updated** - Last modification date
- **Extract Status** - Live or cached data
- **Stale** - Whether it hasn't been updated recently

### Step 3: Filter the List
Use the filter options at the top to narrow down results:

```
Project: [All projects ▼]
Owner:   [All owners ▼]
Status:  [All statuses ▼]
```

Example filters:
- Show only "Interactive Dashboards" project
- Show only workbooks owned by "Smith, John"
- Show only "Stale" workbooks (not updated in 90 days)

### Step 4: Examine a Workbook
1. Click on any workbook name
2. See detailed information:
   - Creation date
   - Last modified date
   - Owner contact info
   - Data source connections
   - View and dashboard count

## Your Second Task: Check User Permissions

### Step 1: Navigate to Permissions
1. Click **Permissions** in the main navigation
2. See all permission rules in your environment

### Step 2: Search for a User
1. Look for filter options (usually at the top)
2. Search for a user by name or email
3. See all permissions assigned to that user

### Step 3: Audit Permissions
Check the permission types:
- ✓ (Allowed) - User has this permission
- ✗ (Denied) - Permission is explicitly blocked
- (blank) - No explicit permission, uses default

## Common Patterns

### Finding Stale Content
1. Go to **Workbooks**
2. Look for "Updated" column with old dates
3. Consider archiving or updating

### Identifying Inactive Users
1. Go to **Users**
2. Check "Last Login" column
3. Users not logged in 90+ days are likely inactive

### Tracking Data Dependencies
1. Go to **Lineage**
2. Click on a workbook
3. See all datasources it depends on
4. Check if datasources are healthy in **Refresh Health**

## Tips & Tricks

### 💡 Use Search
Most pages have search functionality. Use it to quickly find what you need.

### 📊 Export Data
Many tables allow exporting to CSV. Look for an "Export" button.

### 🔄 Refresh Data
Click the **Refresh** button to get latest data from Tableau Server.

### 🔗 Bookmarking
Save filtered views as bookmarks for quick access.

### 📌 Column Sorting
Click column headers to sort (ascending/descending).

## Account Numbers Feature

The dashboard now shows **Account Numbers** in several places:

### Where to Find Account Numbers
1. **Custom Views** - See employee ID for view owners
2. **Users** section - Employee ID next to user info

### Filter by Account Type
In **Custom Views**, use the new filter:
- **Mayo only** - Shows @mayo.edu account holders
- **Non-Mayo only** - Shows external contractors/partners

### What Account Number Means
- **Populated** - Employee ID from BigQuery (Mayo staff)
- **Empty (-)** - No matching employee in BigQuery (external users)

[Learn more about Account Numbers →](../account-numbers/overview.md)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Search on page |
| `Ctrl+R` | Refresh page |
| `?` | Help/Keyboard shortcuts |

## Next Steps

- **[Common Workflows](workflows.md)** - Step-by-step guides for specific tasks
- **[Best Practices](best-practices.md)** - Governance and monitoring tips
- **[Feature Overview](../features/overview.md)** - Detailed explanation of each section

## Need Help?

- **Can't find something?** Use the search bar in the top navigation
- **Have questions?** Check the [Features Overview](../features/overview.md)
- **Specific task?** See [Common Workflows](workflows.md)
- **Account numbers question?** See [Account Numbers Guide](../account-numbers/overview.md)

---

**Pro Tip:** Bookmark the dashboard and set it as your homepage. Check it weekly to stay on top of your Tableau environment! 📌
