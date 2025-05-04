# Dashboard Service Fix

## Problem

The crypto-dashboard service was failing with the following error:
```
AttributeError: 'property' object has no attribute 'schema'
```

## Root Causes

1. **SQLAlchemy Version Incompatibility**: 
   - The system was using SQLAlchemy 2.0.9, but the codebase was designed for SQLAlchemy 1.4.x.
   - SQLAlchemy 2.0 has significant API changes compared to 1.4, causing compatibility issues.

2. **Naming Conflict in Models**: 
   - In `src/database/models.py`, the `SignalLog` class had a property method named `metadata`, which conflicts with SQLAlchemy's internal attribute of the same name.
   - This conflict became problematic in SQLAlchemy 2.0, causing the 'property' object has no attribute 'schema' error.

## Solution

1. **Downgraded SQLAlchemy**:
   - Installed SQLAlchemy 1.4.47 (the latest version in the 1.4.x series) to ensure compatibility:
   ```
   pip install sqlalchemy==1.4.47
   ```

2. **Fixed Property Naming Conflict**:
   - Renamed the `metadata` property method to `get_metadata` in the `SignalLog` class.
   - Added a `to_dict()` method that maintains backward compatibility by mapping the renamed property.

## Verification

- Successfully restarted the crypto-dashboard service
- Service is now running correctly with no errors
- Dashboard is accessible through port 5003

## Future Recommendations

1. **Database Migration**: 
   - Create a proper migration script to handle schema changes safely.

2. **Version Pinning**: 
   - Explicitly pin the SQLAlchemy version in requirements.txt to 1.4.x until a full upgrade to 2.0 can be properly tested.

3. **Testing**: 
   - Add more comprehensive tests for database models to catch compatibility issues earlier.
