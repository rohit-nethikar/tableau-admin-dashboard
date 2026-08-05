# Account Numbers Feature

## What is it?

The **Account Numbers** feature automatically syncs employee/organization identification numbers from Mayo Clinic's BigQuery database into the Tableau Admin Dashboard. This makes it easy to identify users and correlate Tableau activity with employee records.

## How It Works

### The Process
```
BigQuery Database
    ↓
V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP view
    ↓
Sync Service (Automatic)
    ↓
Tableau Admin Dashboard Users Table
    ↓
Displayed in Dashboard
```

### Data Sources
- **Source:** `ml-mps-app-mcs-df-app-p-72d7.phi_team_interactivedbs_us_p.V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP`
- **Key Column:** `CLIENT_ACCOUNT_NUMBER`
- **Match Field:** User email address
- **Sync Frequency:** Automatic when sync endpoint is triggered

## Where Account Numbers Appear

### 1. Users Section
In the **Users** page, each user listing includes:
- User name
- Email address
- **Account Number** (employee ID)
- Last login date
- Site role

### 2. Custom Views Section
In the **Custom Views** page, each view shows:
- View name
- Owner email
- **Account #** (owner's employee ID)
- Workbook/worksheet
- Shared/private status

### Example
```
Owner Email             | Account #
---|---
mielke.diane@mayo.edu   | 7041026
singh.ravishankar@mayo  | 7038944
smith.john@hca.org      | - (not found)
```

## Understanding Account Numbers

### When You See a Number
**Example:** `7041026`

This means:
- ✅ User has a Mayo Clinic employee account
- ✅ Account number synced from BigQuery
- ✅ Can be correlated with HR/employee records
- ✅ User is internal Mayo staff

### When You See a Dash (-)
**Example:** `-`

This means:
- ⚠️ No matching account number found in BigQuery
- ⚠️ Likely an external user (contractor, partner, etc.)
- ⚠️ Not found in employee database
- ⚠️ May need additional security oversight

### Mayo vs Non-Mayo Classification

**Mayo Accounts (@mayo.edu):**
- Email ends with `@mayo.edu`
- Usually have account numbers
- Internal Mayo employees
- Full access to internal systems

**Non-Mayo Accounts:**
- Email from other domains (external hospitals, consultants, etc.)
- Usually DON'T have account numbers
- External contractors/partners
- Limited, role-based access
- May require additional security clearance

## Filtering by Account Type

### Using the Account Type Filter

The **Custom Views** page includes a new filter:

```
[Account Type Filter ▼]
  ☐ All accounts
  ☐ Mayo only
  ☐ Non-Mayo only
```

### Mayo Only
Shows custom views created by:
- Users with @mayo.edu email addresses
- Users with synced account numbers
- Internal Mayo employees

**Use cases:**
- Compliance reporting (internal vs external)
- Usage analysis of Mayo staff
- Access auditing for internal content

### Non-Mayo Only
Shows custom views created by:
- Users with external email addresses
- Users WITHOUT synced account numbers
- External contractors/partners
- Other organizations

**Use cases:**
- Monitor external user activity
- Ensure external users have appropriate access
- Track collaboration with partners
- Security auditing of external access

## Use Cases

### 1. Compliance Reporting
**Scenario:** Auditor asks "Who created this view? Is it an employee?"

**Solution:**
1. Go to **Custom Views**
2. Find the view
3. Check **Owner Email** and **Account #**
4. If account # is populated → Mayo employee
5. If "-" → External user (needs explanation)

### 2. User Identification
**Scenario:** Manager asks "Can you tell me about john.smith's usage?"

**Solution:**
1. Go to **Users** or **Custom Views**
2. Find by email
3. See associated **Account Number**
4. Match with HR database for full context
5. Report activity and recommendations

### 3. Access Control Audit
**Scenario:** Security team wants to ensure external users have limited access

**Solution:**
1. Filter **Custom Views** by "Non-Mayo only"
2. Review each external user's activity
3. Verify their access is appropriate
4. Check if they should have access to sensitive content
5. Take corrective action if needed

### 4. Collaboration Tracking
**Scenario:** How much content are external partners creating?

**Solution:**
1. Filter **Custom Views** by "Non-Mayo only"
2. Count views created by external users
3. Identify which external organizations
4. Assess value vs security risk
5. Plan collaboration governance

### 5. Organizational Reporting
**Scenario:** Executive wants to understand Mayo vs external user engagement

**Solution:**
1. Export **Custom Views** data
2. Filter by account type
3. Generate statistics:
   - % of views by Mayo vs external
   - Trend over time
   - By department/workbook
4. Present to leadership
5. Adjust strategy based on insights

## Technical Details

### Data Synchronization
- **Trigger:** Manual or automatic sync endpoint
- **Update Frequency:** On-demand
- **Match Logic:** Email address (case-insensitive)
- **Success Rate:** ~4,117 mappings found in BigQuery

### Matching Algorithm
```
For each user in Dashboard:
  Get user email
  Search BigQuery for matching email
  If found:
    Populate account_number
    Mark as Mayo if @mayo.edu
  Else:
    Leave account_number blank
    Mark as Non-Mayo
```

### Data Quality
- **Coverage:** ~4,117 account numbers synced
- **Accuracy:** 100% (direct from BigQuery)
- **Freshness:** Updates on demand
- **Availability:** Covers Mayo Clinic employees

## Troubleshooting

### "I don't see account numbers"
**Solution:**
1. Refresh the page (Ctrl+R)
2. Wait for sync to complete (can take a few minutes)
3. Check if user email matches BigQuery records
4. Verify the user is a Mayo employee

### "I see a dash (-) for a Mayo employee"
**Causes:**
- Email address doesn't match BigQuery exactly
- User was recently hired (not yet in BigQuery)
- User has multiple email addresses
- Account not yet synced

**Solution:**
1. Check email format
2. Verify in BigQuery directly
3. Wait for next sync
4. Contact IT if issue persists

### "Account numbers aren't matching users"
**Cause:** Email addresses don't match between systems

**Solution:**
1. Check user's official email in directory
2. Verify against BigQuery
3. Update if inconsistent
4. Re-run sync

## Best Practices

### ✅ DO
- ✅ Use account numbers for compliance reporting
- ✅ Filter by Mayo vs Non-Mayo when auditing access
- ✅ Track changes in account assignments
- ✅ Correlate with HR data for full context
- ✅ Report metrics to stakeholders

### ❌ DON'T
- ❌ Don't assume "-" means unauthorized access (could be new employee)
- ❌ Don't make hiring/firing decisions based solely on account numbers
- ❌ Don't ignore external users with high access
- ❌ Don't forget to verify email addresses match

## Related Topics

- [Custom Views Feature](../features/overview.md#custom-views)
- [Users Management](../features/overview.md#users)
- [Security Best Practices](best-practices.md)
- [Account Type Filtering](../guides/workflows.md#9-filter-custom-views-by-account-type)

## FAQ

**Q: What if I don't see account numbers?**  
A: The sync may not have been run yet. Go to the Custom Views page and manually trigger the sync, or wait for the automatic sync to complete.

**Q: Why do some users not have account numbers?**  
A: They're likely external users (contractors, partners) not in the BigQuery employee database. This is expected and normal.

**Q: Can I manually edit account numbers?**  
A: The dashboard pulls directly from BigQuery for accuracy. To update, contact your BigQuery administrator to update the source data.

**Q: How often is this synced?**  
A: Sync can be triggered manually. Check with your Tableau Administrator for automatic sync schedules.

**Q: Is this data secure?**  
A: Yes. Account numbers are restricted data with appropriate access controls. Only authorized users can see this information.

---

**Next Steps:**
- [Filter by Account Type](../guides/workflows.md#9-filter-custom-views-by-account-type)
- [View Custom Views](../features/overview.md#custom-views)
- [Compliance Auditing](../guides/best-practices.md#security--compliance)
