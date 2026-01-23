# Azure App Service Request - PIBIDS Sprint Dashboard

Hi [Admin Name],

We are migrating our PIBIDS Sprint Dashboard application from the local HPC server to Azure. We would like to request a new **Azure App Service** with the following specifications:

## App Service Requirements

| Item | Specification |
|------|---------------|
| **Service Type** | Azure App Service (Linux) |
| **Runtime** | Python 3.10 or higher |
| **Plan Tier** | Basic B1 or Standard S1 |
| **Region** | West US 2 (preferred, to be near Snowflake) |

## Network Requirements

| Direction | Destination | Port | Purpose |
|-----------|-------------|------|---------|
| **Outbound** | `*.snowflakecomputing.com` | 443 (HTTPS) | Data sync from COH Snowflake |

## Notes

- **Database:** We will use SQLite (file-based) for now; no Azure database service needed at this time. We plan to migrate to Databricks in the future.
- **Storage:** The app includes a small SQLite file (~10 MB). No additional Azure storage service required.
- **Authentication:** Handled within the application (not using Azure AD at this time).

Please let me know if you need any additional information.

Thanks,  
[Your Name]
