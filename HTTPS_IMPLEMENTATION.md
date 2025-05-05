# HTTPS Implementation for the Crypto Trading Dashboard

## Overview

We've implemented HTTPS for the Crypto Trading Dashboard to improve security and fix the "not secure" warning in browsers. This implementation uses self-signed certificates for development/testing purposes.

## Changes Made

1. **SSL Certificate Generation**
   - Created self-signed certificates for local development
   - Stored in the `/certificates` directory
   - Certificate files:
     - `dashboard.crt`: The SSL certificate
     - `dashboard.key`: The private key

2. **Dashboard Server Configuration**
   - Modified `src/dashboard/app.py` to enable SSL support
   - Added conditional logic to use certificates when available
   - Enhanced error handling for certificate loading

3. **Systemd Service Updates**
   - Updated `crypto-dashboard.service` to use SSL with Gunicorn
   - Added the `--certfile` and `--keyfile` parameters to the service configuration
   - Reloaded systemd daemon to apply changes

## Accessing the Dashboard

The dashboard is now accessible via HTTPS at:
- https://localhost:5003/ (when running locally)
- https://your-server-ip:5003/ (when accessing remotely)

## Security Considerations

- The current implementation uses self-signed certificates, which will generate browser warnings
- For production environments, consider:
  - Obtaining proper certificates from a Certificate Authority like Let's Encrypt
  - Setting up Nginx as a reverse proxy with SSL termination
  - Implementing proper certificate renewal processes

## Troubleshooting

If you encounter issues with the HTTPS implementation:

1. **Certificate Errors**: Verify that the certificate files exist in the specified paths
2. **Permission Issues**: Ensure the service user has read access to the certificate files
3. **Service Startup Failures**: Check the service logs with `sudo journalctl -u crypto-dashboard.service`

## Next Steps

For enhanced security in production:
1. Replace self-signed certificates with CA-signed certificates
2. Configure automatic certificate renewal
3. Implement HTTP to HTTPS redirection
4. Add HSTS headers for additional security
