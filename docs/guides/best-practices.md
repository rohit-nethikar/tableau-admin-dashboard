# Best Practices & Governance

This guide provides recommendations for effective governance and monitoring of your Tableau environment.

## Regular Monitoring Schedule

### Daily (5 minutes)
- Check **Refresh Health** for failed extracts
- Look for critical **Findings** or alerts
- Review any error notifications

### Weekly (30 minutes)
- Review **Workbooks** for activity
- Check **Users** last login dates
- Monitor **Custom Views** creation
- Review **Findings** section
- Verify **Health** status

### Monthly (1-2 hours)
- Full audit of **Permissions**
- Review stale content
- Analyze **Lineage** for optimization opportunities
- Generate reports for stakeholders
- Plan maintenance and archival

### Quarterly (2-4 hours)
- Comprehensive governance review
- License utilization analysis
- User access audit
- Datasource consolidation review
- Disaster recovery testing

---

## Permission Management

### Principle of Least Privilege
**Rule:** Users should have minimum permissions needed for their job.

**How to implement:**
1. Start with Viewer role (read-only)
2. Upgrade to Creator/Explorer only if needed
3. Regularly audit permissions
4. Remove access when users change roles

### Recommended Permission Levels

| Role | Typical User | Recommended Permissions |
|------|--------------|------------------------|
| Admin | IT/Tableau admins | All permissions |
| Creator | Content developers | Create, Edit, Share |
| Explorer | Power users | View, Interact, Download |
| Viewer | General users | View only |

### Quarterly Permission Audit
1. Go to **Permissions**
2. Review all Admin-level users:
   - Are they still Admin?
   - Should they be downgraded?
3. Review high-access Creator accounts
4. Identify unused accounts to remove

---

## Content Management

### Stale Content Policy
**Rule:** Remove or update workbooks not modified in 90 days.

**Process:**
1. Go to **Workbooks**
2. Filter by "Updated" column - find old dates
3. For each stale workbook:
   - Contact owner
   - Ask if still needed
   - Schedule archival or update
   - Document decision
4. Archive or delete
5. Log action for audit

### Naming Conventions
**Recommendation:** Use consistent naming to make content searchable.

**Example format:**
```
[Department] - [Content Type] - [Subject] - [Version]
Finance - Dashboard - Monthly Budget Summary - v2.1
```

### Documentation
**Requirement:** Each workbook should have:
- Clear description
- Owner/contact info
- Refresh schedule
- Data source information
- Last updated date

### Version Control
**Best Practice:**
- Keep only current version active
- Archive old versions
- Use naming to distinguish versions
- Document version history

---

## Datasource Management

### Extract Refresh Health
**Goal:** 99%+ success rate

**Actions:**
1. Monitor **Refresh Health** daily
2. Set alerts for consecutive failures (>2)
3. Investigate failures immediately:
   - Check source database availability
   - Verify connection credentials
   - Review error logs
4. Prevent issues:
   - Schedule refreshes during off-peak hours
   - Allow sufficient time between refreshes
   - Monitor resource usage

### Datasource Consolidation
**Goal:** Reduce redundancy and improve performance

**Process:**
1. Use **Lineage** to find overlapping datasources
2. Identify opportunities to consolidate
3. Plan migration:
   - Create unified datasource
   - Update workbooks to use new source
   - Archive old datasources
4. Verify performance after consolidation

### Datasource Documentation
Each datasource should include:
- Data refresh schedule
- Owner contact info
- Data source location (database/API)
- Last successful refresh time
- Known limitations or caveats

---

## User Access Management

### New User Onboarding
1. Add user to Tableau Server
2. Assign minimal role (Viewer initially)
3. Grant access to specific workbooks only
4. Document decision
5. Schedule 30-day review

### Offboarding Process
1. Get notification of departing employee
2. Review their **Permissions** in dashboard
3. Document all access they have
4. Remove all permissions
5. Transfer ownership of critical content:
   - Reassign workbooks
   - Reassign datasources
   - Document transfers
6. Deactivate account
7. Archive for compliance

### Inactive User Management
**Rule:** Remove licenses for users inactive 90+ days

**Process:**
1. Monthly: Export **Users** list
2. Filter by Last Login > 90 days
3. Verify they should still be active:
   - Check with manager
   - Review their job function
4. Decide on each:
   - Keep (still needed)
   - Downgrade (reduce license level)
   - Remove (no longer needed)
5. Execute changes
6. Document decisions

---

## Security & Compliance

### Permission Audit Checklist
- [ ] No users have unnecessary Admin role
- [ ] External users have minimal permissions
- [ ] Sensitive data access is restricted
- [ ] Shared content is appropriate
- [ ] Users only access content for their role
- [ ] Former employees removed
- [ ] Access reviewed in past 6 months

### Data Security Best Practices
1. **Encryption:** Enable SSL/TLS for all connections
2. **Authentication:** Use SSO where possible
3. **Audit Logging:** Enable and review audit logs
4. **Sensitive Data:** Restrict access to filtered views
5. **Compliance:** Follow data retention policies

### Account Numbers for User Identification
**New Feature:** BigQuery-synced employee IDs

**Use cases:**
- **Compliance Reporting:** Track internal vs external usage
- **User Identification:** Quickly match views to employees
- **HR Integration:** Correlate with employee records
- **Access Auditing:** Verify correct employee has access

**Where found:**
- Users section (employee ID for each account)
- Custom Views (employee ID of view creator)
- Filtered view (Mayo only = @mayo.edu employees)

[Learn more about Account Numbers →](../account-numbers/overview.md)

---

## Monitoring & Alerts

### Key Metrics to Track

| Metric | Threshold | Action |
|--------|-----------|--------|
| Failed Extract Refreshes | >2 consecutive failures | Investigate immediately |
| Stale Workbooks | 90+ days without update | Contact owner |
| Inactive Users | 90+ days no login | Plan removal |
| Permission Violations | Any overly permissive | Schedule audit |
| System Health | Any red indicators | Check immediately |

### Alert Setup
1. Check your monitoring system for alerts
2. Configure notifications for:
   - Extract refresh failures
   - Permission changes
   - User access requests
   - System health issues
3. Establish escalation path:
   - First alert → Check dashboard
   - Multiple failures → Contact owner
   - Critical issue → Escalate to IT

---

## Reporting & Communication

### Weekly Status Report
**Send to:** Governance team/stakeholders

**Include:**
- Extract refresh success rate
- New workbooks created
- Permissions changes made
- Any critical findings
- Upcoming maintenance

### Monthly Governance Report
**Send to:** Leadership/compliance

**Include:**
- User activity statistics
- Permission audit results
- Content archival actions
- Any security incidents
- Recommendations

### Quarterly Business Review
**Meeting:** Tableau stakeholders

**Topics:**
- License utilization
- Usage trends
- Performance metrics
- Planned improvements
- Budget/resource needs

---

## Optimization & Planning

### Performance Optimization
1. Use **Lineage** to find inefficiencies
2. Consolidate redundant datasources
3. Archive unused workbooks
4. Optimize slow extracts:
   - Reduce data volume
   - Add incremental refresh
   - Schedule off-peak
5. Monitor impact

### Capacity Planning
1. Track user growth
2. Monitor extract refresh time
3. Plan for seasonal peaks
4. Size infrastructure appropriately
5. Plan ahead for license needs

### Disaster Recovery
1. Document critical content:
   - Workbooks used by executives
   - Datasources for compliance reporting
   - High-impact dashboards
2. Test backup/restore procedures monthly
3. Document recovery procedures
4. Train team on recovery process
5. Plan for failover scenarios

---

## Governance Framework

### Roles & Responsibilities

**Tableau Administrator:**
- Overall system management
- Permission management
- User provisioning/deprovisioning
- Performance optimization
- Disaster recovery

**Content Owner:**
- Maintain workbook documentation
- Keep content current (update within 90 days)
- Remove stale content
- Manage data quality
- Provide training

**Data Steward:**
- Datasource management
- Extract refresh health
- Data quality monitoring
- Documentation
- Performance tuning

**Governance Lead:**
- Compliance monitoring
- Permission audits
- Policy enforcement
- Risk management
- Stakeholder communication

### Decision Tracking
Document all major decisions:
- Archive decisions (what was archived, why, when)
- Permission changes (who, what, why, when)
- Datasource consolidations
- Major configuration changes
- Compliance actions

---

## Checklist: Governance Essentials

- [ ] Establish permission approval workflow
- [ ] Define and communicate content retention policy
- [ ] Create user onboarding/offboarding procedures
- [ ] Set up monitoring and alerts
- [ ] Schedule regular audits (weekly/monthly/quarterly)
- [ ] Document decisions and actions
- [ ] Train team on policies and procedures
- [ ] Review and update policies annually
- [ ] Maintain disaster recovery plan
- [ ] Report metrics to stakeholders

---

## Resources

- [Feature Overview](../features/overview.md) - Detailed feature information
- [Common Workflows](workflows.md) - Step-by-step task guides
- [Account Numbers Guide](../account-numbers/overview.md) - Understanding employee IDs
- [Getting Started](getting-started.md) - Dashboard navigation basics

---

**Remember:** Good governance is an ongoing process. Regular monitoring, clear communication, and consistent enforcement of policies ensure a healthy Tableau environment.
