# PIBIDS Sprint Dashboard - Azure Migration Specification

## 1. Application Overview

| Attribute | Details |
|-----------|---------|
| **Application Name** | PIBIDS Sprint Dashboard |
| **Framework** | Streamlit (Python) |
| **Purpose** | Sprint planning, task tracking, and worklog management for Lab Path Informatics team |
| **Current Environment** | On-premises HPC server |
| **Users** | ~10-15 internal team members |

---

## 2. Recommended Azure Services

### 2.1 Compute - Azure App Service (Web App)

**Recommended Service:** Azure App Service (Linux)

| Requirement | Specification |
|-------------|---------------|
| **Runtime** | Python 3.10+ |
| **Framework** | Streamlit |
| **Plan Tier** | Basic B1 or Standard S1 |
| **vCPUs** | 1-2 |
| **Memory** | 1.75 - 3.5 GB |
| **Storage** | 10 GB |

**Why App Service:**
- Native Python support
- Easy deployment via GitHub Actions or Azure DevOps
- Built-in SSL/TLS
- Auto-scaling capability if needed
- Cost-effective for small team applications

**Alternative:** Azure Container Instances (ACI) or Azure Kubernetes Service (AKS) if containerization is preferred.

---

### 2.2 Database - Azure SQL Database or Azure Database for PostgreSQL

**Current State:** SQLite (local file-based, ~8 MB)

**Recommended Service:** Azure SQL Database (Basic/Standard tier) or Azure Database for PostgreSQL (Flexible Server)

| Requirement | Specification |
|-------------|---------------|
| **Data Volume** | ~25,000 records total |
| **Tables** | tasks (12,600), tickets (11,700), worklogs (1,800), sprints |
| **Access Pattern** | Read-heavy, periodic sync writes |
| **Tier** | Basic (5 DTUs) or Standard S0 |
| **Storage** | 2 GB (with room to grow) |

**Migration Notes:**
- Current SQLite schema can be migrated to Azure SQL or PostgreSQL
- Minor SQL syntax adjustments may be needed
- Connection string update in application config

**Alternative (Simple):** Keep SQLite with Azure File Storage mount if minimal changes preferred.

---

### 2.3 External Data Connection - Snowflake

**Requirement:** The application connects to City of Hope's Snowflake data warehouse to sync iTrack ticket/task data.

| Requirement | Specification |
|-------------|---------------|
| **Connection Type** | Outbound HTTPS (port 443) |
| **Authentication** | Username/Password (stored in Azure Key Vault) |
| **Frequency** | On-demand (user-triggered sync) |
| **Data Flow** | Read-only from Snowflake → Write to Azure DB |

**Network Requirements:**
- Allow outbound connections to Snowflake endpoints (`*.snowflakecomputing.com`)
- Snowflake account URL: `cityofhope.west-us-2.azure.snowflakecomputing.com`

**Credentials Storage:**
- Store Snowflake credentials in **Azure Key Vault**
- App Service retrieves secrets at runtime
- Never store credentials in code or config files

---

### 2.4 Secrets Management - Azure Key Vault

**Required Secrets:**

| Secret Name | Description |
|-------------|-------------|
| `SNOWFLAKE_USER` | Snowflake service account username |
| `SNOWFLAKE_PASSWORD` | Snowflake service account password |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_WAREHOUSE` | Snowflake warehouse name |
| `SNOWFLAKE_DATABASE` | Database name |
| `SNOWFLAKE_SCHEMA` | Schema name |
| `DB_CONNECTION_STRING` | Azure SQL/PostgreSQL connection string |

---

### 2.5 Storage - Azure Blob Storage (Optional)

**Purpose:** Store uploaded CSV files, exports, and backups

| Requirement | Specification |
|-------------|---------------|
| **Storage Type** | Blob Storage (Hot tier) |
| **Estimated Size** | < 1 GB |
| **Access** | Private (app-only access) |

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Azure Cloud                              │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Azure      │    │   Azure      │    │   Azure      │       │
│  │  App Service │───▶│  SQL Database│    │  Key Vault   │       │
│  │  (Streamlit) │    │  or PostgreSQL│    │  (Secrets)   │       │
│  └──────┬───────┘    └──────────────┘    └──────────────┘       │
│         │                                        ▲               │
│         │                                        │               │
│         │            ┌──────────────┐            │               │
│         └───────────▶│ Azure Blob   │            │               │
│                      │ Storage      │            │               │
│                      └──────────────┘            │               │
│                                                  │               │
└──────────────────────────────────────────────────┼───────────────┘
                                                   │
                              ┌────────────────────┼────────────────┐
                              │                    │                │
                              │    ┌───────────────▼─────────────┐  │
                              │    │      Snowflake              │  │
                              │    │   (COH Data Warehouse)      │  │
                              │    │   - DS_VW_ITRACK_LPM_TASK   │  │
                              │    │   - DS_VW_ITRACK_PLMGETINCIDENT│
                              │    │   - DS_VW_ITRACK_LPM_WORKLOG│  │
                              │    └─────────────────────────────┘  │
                              │         External (Read-Only)        │
                              └─────────────────────────────────────┘
```

---

## 4. Python Dependencies

```
# Core Framework
streamlit>=1.30.0

# Data Processing
pandas==2.1.4
numpy==1.26.2

# Visualization
plotly==5.18.0
altair==5.2.0

# Enhanced Components
streamlit-aggrid==0.3.4.post3
streamlit-option-menu==0.3.6
streamlit-extras==0.3.6

# Data Validation
pydantic==2.5.3
python-dateutil==2.8.2

# Export
openpyxl==3.1.2
reportlab==4.0.7

# Authentication
streamlit-authenticator==0.2.3

# Database Connectors
snowflake-connector-python>=3.6.0
pyodbc  # For Azure SQL (add if using Azure SQL)
psycopg2-binary  # For PostgreSQL (add if using PostgreSQL)

# Utilities
pytz==2023.3
tomli==2.0.1
```

---

## 5. Network & Security Requirements

### 5.1 Inbound Traffic
| Source | Port | Protocol | Purpose |
|--------|------|----------|---------|
| Users (Internal) | 443 | HTTPS | Web application access |

### 5.2 Outbound Traffic
| Destination | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| Snowflake (`*.snowflakecomputing.com`) | 443 | HTTPS | Data sync |
| Azure SQL/PostgreSQL | 1433/5432 | TCP | Database |

### 5.3 Authentication
- **User Authentication:** Built-in Streamlit Authenticator (username/password)
- **Future Option:** Azure AD integration for SSO

---

## 6. Estimated Azure Costs (Monthly)

| Service | Tier | Estimated Cost |
|---------|------|----------------|
| App Service | Basic B1 | $13 - $55 |
| Azure SQL Database | Basic (5 DTU) | $5 |
| Azure Key Vault | Standard | $0.03/secret/month |
| Azure Blob Storage | Hot, <1GB | < $1 |
| **Total** | | **~$20 - $60/month** |

*Costs may vary based on usage and region.*

---

## 7. Deployment Options

### Option A: Azure App Service (Recommended)
1. Create Azure App Service (Linux, Python 3.10)
2. Deploy via GitHub Actions or Azure DevOps
3. Configure environment variables from Key Vault
4. Set startup command: `streamlit run Home.py --server.port 8000`

### Option B: Azure Container Instance
1. Build Docker image with Streamlit app
2. Push to Azure Container Registry
3. Deploy to ACI with environment variables

### Option C: Azure Virtual Machine (Most flexible, higher maintenance)
1. Provision Linux VM (B2s or similar)
2. Install Python, dependencies manually
3. Run Streamlit as a service

---

## 8. Migration Checklist

- [ ] Provision Azure App Service
- [ ] Create Azure SQL Database or PostgreSQL
- [ ] Set up Azure Key Vault with secrets
- [ ] Configure network rules for Snowflake access
- [ ] Migrate SQLite data to Azure database
- [ ] Update application connection strings
- [ ] Test Snowflake connectivity from Azure
- [ ] Configure custom domain (optional)
- [ ] Set up SSL certificate
- [ ] User acceptance testing
- [ ] Go-live

---

## 9. Contact & Support

| Role | Contact |
|------|---------|
| Application Owner | [Your Name] |
| Azure Admin | [Azure Admin Name] |
| Snowflake Admin | Ritesh |

---

*Document Version: 1.0*  
*Date: January 22, 2026*
