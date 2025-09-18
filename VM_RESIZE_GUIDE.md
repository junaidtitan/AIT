# Safe VM Resize Guide for GCP Compute Instance

## Current VM Specifications
- **Instance**: yta-main
- **Type**: c4-standard-2
- **Zone**: us-central1-a
- **CPUs**: 2 cores
- **RAM**: 7GB
- **Disk**: 10GB (74% used)
- **Status**: RUNNING

## Recommended Upgrade Options

### Option 1: c4-standard-4 (Moderate Upgrade)
- **CPUs**: 4 cores (2x increase)
- **RAM**: 15GB (2x increase)
- **Use Case**: Better for parallel processing, LangGraph agents

### Option 2: c4-standard-8 (Significant Upgrade)
- **CPUs**: 8 cores (4x increase)
- **RAM**: 30GB (4x increase)
- **Use Case**: Heavy AI workloads, multiple concurrent pipelines

## Safe Resize Procedure (5-10 minutes downtime)

### Pre-Resize Checklist
✅ Backup created: `AIT_pre_resize_backup_20250918_185748.tar.gz`
✅ No active pipeline runs
✅ Git status clean (check with `git status`)

### Step-by-Step Resize Process

```bash
# 1. Stop the VM (from Cloud Console or gcloud)
gcloud compute instances stop yta-main --zone=us-central1-a

# 2. Resize the machine type
gcloud compute instances set-machine-type yta-main \
    --machine-type=c4-standard-4 \
    --zone=us-central1-a

# 3. Start the VM
gcloud compute instances start yta-main --zone=us-central1-a

# 4. Wait for SSH to be ready (1-2 minutes)
gcloud compute ssh yta-main --zone=us-central1-a --command="echo 'VM is ready'"
```

### Alternative: Using Google Cloud Console (Easier)

1. Go to: https://console.cloud.google.com/compute/instances
2. Find `yta-main` instance
3. Click the instance name
4. Click "STOP" button at the top
5. Wait for status to show "TERMINATED"
6. Click "EDIT" button
7. Under "Machine configuration" → "Machine type", select new type
8. Click "SAVE"
9. Click "START" button

## Post-Resize Verification

```bash
# 1. SSH back into the VM
gcloud compute ssh yta-main --zone=us-central1-a

# 2. Verify new specs
free -h
nproc
df -h

# 3. Test AIT pipeline
cd /home/junaidqureshi/AIT
python3 test_pipeline_minimal.py

# 4. Check services
env | grep API_KEY
```

## Important Notes

### What's Preserved:
- ✅ All files and data on disk
- ✅ Environment variables
- ✅ Installed packages
- ✅ Git repositories
- ✅ API keys and secrets
- ✅ User accounts and permissions

### What Changes:
- ⚠️ Internal IP might change (usually doesn't)
- ⚠️ SSH connections will drop during resize
- ⚠️ Any running processes will be terminated

### Disk Space Consideration
Current disk usage is 74%. If you also need more disk space:

```bash
# Resize disk (can be done while VM is running!)
gcloud compute disks resize yta-main --size=20GB --zone=us-central1-a

# Then inside VM, resize the filesystem
sudo resize2fs /dev/sda1
```

## Rollback Plan

If issues occur after resize:

```bash
# Stop VM
gcloud compute instances stop yta-main --zone=us-central1-a

# Revert to original machine type
gcloud compute instances set-machine-type yta-main \
    --machine-type=c4-standard-2 \
    --zone=us-central1-a

# Start VM
gcloud compute instances start yta-main --zone=us-central1-a

# Restore from backup if needed
cd /home/junaidqureshi
tar -xzf AIT_pre_resize_backup_20250918_185748.tar.gz
```

## Cost Implications

- **c4-standard-2**: ~$86/month
- **c4-standard-4**: ~$172/month (2x cost)
- **c4-standard-8**: ~$344/month (4x cost)

*Prices are estimates for us-central1 region*

## Recommended Action

Given your LangGraph implementation plans and current resource constraints:
1. **Upgrade to c4-standard-4** for immediate improvement
2. Consider disk resize to 20GB for breathing room
3. Monitor performance, upgrade to c4-standard-8 if needed later

---

**Created**: September 18, 2025
**Backup Location**: `/home/junaidqureshi/AIT_pre_resize_backup_20250918_185748.tar.gz`