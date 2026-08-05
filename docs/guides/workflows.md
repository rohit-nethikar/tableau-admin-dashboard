# Common Workflows

This guide provides step-by-step instructions for common tasks in the Tableau Admin Dashboard.

## 1. Find Stale Content (Not Updated in 90 Days)

**Purpose:** Identify workbooks that might be unused or need updating

**Steps:**

1. Go to **Workbooks**
2. Look at the "Updated" column - note the dates
3. Alternatively, filter if "Stale" column exists:
   - Filter Status → Select "Stale"
4. Review the list:
   - Check if workbook is still needed
   - Contact owner to ask if it's still in use
   - Plan to archive or update
5. Take action:
   - Archive if no longer needed
   - Update if still relevant
   - Create new version if outdated

**Expected Output:**
- List of workbooks not updated in 90+ days
- Owner information
- Context for archival decisions

---

## 2. Audit User Permissions

**Purpose:** Ensure users have appropriate access levels

**Steps:**

1. Go to **Permissions**
2. Filter by specific user:
   - Look for search/filter options
   - Enter user name or email
3. Review what permissions they have:
   - ✓ (Allowed) - They have this permission
   - ✗ (Denied) - Explicitly blocked
   - (blank) - Uses default rules
4. Identify concerns:
   - Do they have Admin when only Creator is needed?
   - Do they have access to sensitive content?
   - Is access still needed?
5. Take action:
   - Discuss with team lead
   - Adjust permissions if needed
   - Document the change

**Expected Output:**
- List of all permissions for a user
- Identification of unusual or overly permissive access

---

## 3. Troubleshoot Data Refresh Failures

**Purpose:** Identify and fix failing datasource extracts

**Steps:**

1. Go to **Refresh Health**
2. Look for "Status" column:
   - Red/Failed = Extract failed to refresh
   - Green/Success = Successfully refreshed
   - Yellow/Running = Currently refreshing
3. Click on a failed datasource
4. Check details:
   - When did it fail?
   - How many times in a row? (Consecutive Failures)
   - What error message appears?
5. Investigate causes:
   - Go to **Lineage** to understand dependencies
   - Check if source database is down
   - Review datasource connection settings
6. Take action:
   - Contact datasource owner
   - Fix database connection if needed
   - Trigger manual refresh if needed
   - Set up alerts for failures

**Expected Output:**
- Identified cause of refresh failure
- Action plan to fix the issue

---

## 4. Understand Data Dependencies

**Purpose:** See how data flows from source to dashboard

**Steps:**

1. Go to **Lineage**
2. Click on a workbook you want to understand
3. You'll see:
   - Data sources feeding into this workbook
   - Databases/systems providing the data
   - Other workbooks depending on same sources
4. Analyze the chain:
   - Start: Database/external system
   - Middle: Published datasource
   - End: Workbook/Dashboard
5. Use this to:
   - Plan maintenance (know what breaks if datasource changes)
   - Troubleshoot (find where data issues originate)
   - Optimize (consolidate redundant datasources)

**Expected Output:**
- Visual/text representation of data flow
- List of all dependencies

---

## 5. Find Who Owns a Workbook

**Purpose:** Locate the contact for a specific workbook

**Steps:**

1. Go to **Workbooks**
2. Find the workbook in the list
3. Look at "Owner" column
4. Click on owner name (if clickable)
5. You'll see:
   - Owner email
   - Owner contact info
   - Other workbooks they own
6. Reach out to owner:
   - Ask about workbook usage
   - Request updates if stale
   - Discuss permissions

**Expected Output:**
- Owner contact information
- Context about workbook maintenance

---

## 6. Monitor Extract Refresh Performance

**Purpose:** Track which extracts are healthy and which are failing

**Steps:**

1. Go to **Refresh Health**
2. Review the table:
   - Datasource name
   - Last refresh status
   - When it last ran
   - Consecutive failures
3. Identify problem datasources:
   - Multiple consecutive failures
   - Not refreshed recently
   - Long refresh duration
4. Analyze trends:
   - Do failures happen at specific times?
   - Are certain datasources always failing?
   - Is performance degrading?
5. Create action plan:
   - Fix failing datasources
   - Optimize slow refreshes
   - Schedule better refresh times
   - Set up alerts

**Expected Output:**
- Health assessment of all extracts
- List of problem datasources
- Prioritized action items

---

## 7. Identify Inactive Users

**Purpose:** Find users who haven't logged in recently

**Steps:**

1. Go to **Users**
2. Look at "Last Login" column
3. Identify users who haven't logged in in 90+ days
4. Cross-reference:
   - Check if they're supposed to be active
   - Ask their manager if still needed
   - Review their permissions in **Permissions**
5. Take action:
   - Remove if no longer needed
   - Re-activate if person returns
   - Downgrade license level if appropriate

**Expected Output:**
- List of inactive users
- Recommendation for each (keep/remove/downgrade)

---

## 8. Identify Custom Views by User

**Purpose:** Find all custom views created by a specific user

**Steps:**

1. Go to **Custom Views**
2. Filter by "Owner":
   - Select specific owner name
3. Or use search to find user email
4. View results:
   - All views created by that user
   - Which workbooks contain them
   - Shared or private status
   - Associated employee account number (if available)
5. Analyze:
   - How many views did they create?
   - Are they shared widely?
   - Are they still relevant?

**Expected Output:**
- List of custom views by specific user

---

## 9. Filter Custom Views by Account Type

**Purpose:** Separate Mayo employees from external contractors

**Steps:**

1. Go to **Custom Views**
2. Find the "Account Type" filter (near top)
3. Choose filter option:
   - **"Mayo only"** - Shows @mayo.edu accounts with employee IDs
   - **"Non-Mayo only"** - Shows external accounts
   - **"All accounts"** - No filtering
4. View results:
   - Mayo: Will show employee account numbers
   - Non-Mayo: Won't have account numbers (external)
5. Use this for:
   - Compliance (track internal vs external use)
   - Reporting (how much content external users create)
   - Security (audit external access)

**Expected Output:**
- Filtered list of custom views
- Clear separation of Mayo vs external users

---

## 10. Export Data for Reporting

**Purpose:** Get data into Excel/CSV for analysis

**Steps:**

1. Go to any table view (Workbooks, Users, Custom Views, etc.)
2. Look for **Export** or **Download** button
3. Choose format:
   - CSV (comma-separated, opens in Excel)
   - PDF (for printing)
4. Click to download
5. Open file in Excel/Google Sheets
6. Analyze:
   - Create pivot tables
   - Make charts
   - Send to stakeholders
   - Archive for compliance

**Expected Output:**
- CSV/PDF file with all data from that view
- Ready for analysis in spreadsheet tools

---

## 11. Track Content Shared with Specific Users

**Purpose:** See what content a user has access to

**Steps:**

1. Go to **Permissions**
2. Filter by user name/email
3. Review all permission entries:
   - Shows every workbook/datasource they can access
   - Shows permission types (View, Edit, Share, etc.)
4. Analyze access:
   - Do they need all this access?
   - Should any be removed?
   - Are permissions appropriate for their role?
5. Take action:
   - Discuss with manager
   - Remove unnecessary permissions
   - Document access

**Expected Output:**
- Complete list of user's access rights

---

## 12. Monitor User Activity

**Purpose:** Track who's actually using Tableau

**Steps:**

1. Go to **Users**
2. Check "Last Login" column:
   - Recent dates = actively using
   - Old dates = not using
   - Never = never logged in
3. Analyze patterns:
   - Are users actually engaged?
   - Are licenses being fully utilized?
   - Are there cost optimization opportunities?
4. Report findings:
   - Identify unused licenses
   - Plan license reductions
   - Target training for inactive users
   - Reallocate seats to new users

**Expected Output:**
- User engagement assessment
- Recommendations for license optimization

---

## Quick Reference Table

| Task | Section | Key Column | Filter |
|------|---------|-----------|--------|
| Find old workbooks | Workbooks | Updated | Date range |
| Check user permissions | Permissions | Permission Type | User name |
| Monitor health | Refresh Health | Status | Failed |
| Find content creator | Custom Views | Owner | User name |
| Track usage | Users | Last Login | Date range |
| Understand dependencies | Lineage | Connections | Workbook |

---

**Next Steps:**
- [Best Practices](best-practices.md) - Governance recommendations
- [Account Numbers Guide](../account-numbers/overview.md) - Understanding employee IDs
- [Features Overview](../features/overview.md) - Detailed feature information
