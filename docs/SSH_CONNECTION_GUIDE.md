# SSH Connection Guide for EC2 Instance

This guide provides instructions for resolving SSH connection issues when connecting to your EC2 instance.

## Host Key Verification Failed

You're seeing the "Host key verification failed" error because the SSH key for the IP address has changed. This is normal when connecting to a newly created EC2 instance that has the same IP as a previously accessed instance.

## Solution 1: Remove the old host key

```bash
# Remove the old host key for the IP address
ssh-keygen -R 3.220.9.26
```

This command removes the old host key for the IP address from your known_hosts file.

## Solution 2: Locate your private key file

The error message indicates that the private key file `Trading_App_PairKey1.pem` is not found. You need to:

1. Locate the private key file that was created when you launched the EC2 instance
2. Make sure it has the correct permissions

```bash
# Set the correct permissions for your key file (once you've located it)
chmod 400 /path/to/Trading_App_PairKey1.pem
```

## Solution 3: Use the AWS Console to connect

If you can't locate your private key file, you can:

1. Go to the AWS EC2 Console
2. Select your instance (i-0a647be0188f8831b)
3. Click "Connect"
4. Choose "EC2 Instance Connect" or "Session Manager"
5. Click "Connect" to open a browser-based terminal session

## Solution 4: Create a new key pair

If you can't find your original key pair:

1. Create a new key pair in the AWS Console
2. Stop your EC2 instance
3. Detach the root volume
4. Attach the root volume to a temporary instance
5. Add your new public key to the authorized_keys file
6. Reattach the volume to your original instance
7. Start your instance
8. Connect using your new key pair

## Verifying the Host Key

The fingerprint for the ED25519 key sent by the remote host is:
```
SHA256:V4wVEAl13Drp10nddioBf/UmK8LIUcRdAm5Y8XqUvTo
```

You can verify this fingerprint against the console output of your instance:

```bash
aws ec2 get-console-output --instance-id i-0a647be0188f8831b
```

Look for the SSH host key fingerprints in the output to confirm this is the correct fingerprint.

## Correct SSH Command

Once you've located your key file and removed the old host key, use:

```bash
ssh -i /path/to/Trading_App_PairKey1.pem ubuntu@3.220.9.26
```

When prompted to confirm the new host key, type "yes" to add it to your known_hosts file.
