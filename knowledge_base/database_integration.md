# Database Integration Guide

## Supported Databases
- PostgreSQL 13+
- MySQL 8.0+
- MongoDB 5.0+
- Amazon RDS (all supported engines)
- Google Cloud SQL
- Azure SQL Database
- Snowflake
- BigQuery

## Connection Setup

### PostgreSQL / MySQL
```
Host: your-db-host.amazonaws.com (or your-db-host.cloud.google.com)
Port: 5432 (PostgreSQL) or 3306 (MySQL)
Database: your_database_name
Username: your_db_user
Password: your_db_password
SSL: Required
```

### MongoDB
```
Connection String: mongodb+srv://user:pass@cluster.mongodb.net/dbname
Options: SSL=true, retryWrites=true
```

## Configuration in AdSparkX
1. Go to Dashboard > Integrations > Databases.
2. Click "Add Database Connection."
3. Select database type.
4. Enter connection details.
5. Click "Test Connection."
6. Save configuration.

## Security Requirements
- IP whitelist: Add AdSparkX IPs to your database firewall.
- SSL/TLS encryption is mandatory.
- Read-only credentials are recommended for data sources.
- Connection pooling: max 10 concurrent connections.
- Idle connection timeout: 5 minutes.

## Troubleshooting

### Connection Timeout
- Verify firewall rules allow inbound connections.
- Check that SSL/TLS is enabled.
- Ensure the database server is running.

### Authentication Failed
- Verify username and password.
- Check that the user has remote access permissions.
- For MySQL: GRANT ALL ON db.* TO 'user'@'%';

### Query Performance Issues
- Add indexes on frequently queried columns.
- Limit result sets with pagination.
- Avoid N+1 query patterns.
