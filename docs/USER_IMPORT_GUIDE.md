# User Import Tool Guide

The `import_users` command is a powerful utility for bulk importing users, teams, groups, and their relationships into the CRM system from a JSON file.

## Command Location
`users/management/commands/import_users.py`

## Basic Usage
Run the command using `manage.py`:

```bash
python manage.py import_users <path_to_json_file>
```

## Available Arguments

| Argument | Description |
|----------|-------------|
| `import_file` | Path to the JSON export file to import (Required) |
| `--role <role>` | **NEW**: Filter import to only include users with a specific role (e.g., `salesperson`). |
| `--dry-run` | Perform a dry run without making any changes. Useful for verifying what will happen. |
| `--update-existing` | Update details of existing users instead of skipping them. |
| `--default-password <password>` | Set a default password for users without password hashes. Default is `ChangeMe123!`. |
| `--skip-relationships` | Skip importing team relationships and memberships. |
| `--force` | Force import even if validation warnings exist. |

## Filtering by Role (Salesperson Only)
To import **only** users with the "salesperson" role, use the `--role` argument:

```bash
python manage.py import_users data.json --role salesperson
```

This will:
1.  Scan the `data.json` file.
2.  Filter out any user whose role is NOT "salesperson".
3.  Import only the matching salesperson accounts.

## Examples

### 1. Dry Run (Safe Test)
Check what would happen if you imported the file, without actually changing anything:
```bash
python manage.py import_users users_export.json --dry-run
```

### 2. Import Salespeople Only
Import only the salespeople from a large dump file:
```bash
python manage.py import_users users_export.json --role salesperson
```

### 3. Full Import with Updates
Import everyone and update existing user details if they have changed:
```bash
python manage.py import_users users_export.json --update-existing
```

## JSON File Format
The import file should be a JSON object with the following structure:
```json
{
  "export_info": { ... },
  "users": [
    {
      "username": "jdoe",
      "email": "jdoe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "salesperson",
      "is_active": true,
      ...
    }
  ],
  "teams": [ ... ],
  "groups": [ ... ],
  "memberships": [ ... ]
}
```
