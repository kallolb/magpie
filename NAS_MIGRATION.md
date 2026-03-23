# Migrating to NAS Storage

This guide walks you through moving your video library from local storage to a NAS (Network Attached Storage) device.

## How Storage Works

The app stores everything under a single `STORAGE_ROOT` directory:

```
{STORAGE_ROOT}/
├── db/videos.db          # SQLite database + search index
├── thumbnails/           # Video thumbnail images
├── videos/               # Video files organized by category
│   ├── tutorials/
│   ├── music/
│   └── ...
└── config/               # Runtime configuration
```

All file paths in the database are **relative** to the storage root, so you can move the entire directory tree to a new location without breaking anything.

---

## Option A: NFS Mount (Recommended for Linux/Docker)

This is the cleanest approach — mount your NAS as an NFS share and point Docker at it.

### Step 1: Enable NFS on Your NAS

**Synology DSM:**
1. Control Panel → File Services → NFS → Enable NFS
2. Shared Folders → select your target folder → Edit → NFS Permissions
3. Add: hostname=`*` or your server IP, privilege=Read/Write, squash=No mapping

**TrueNAS / FreeNAS:**
1. Sharing → Unix Shares (NFS) → Add
2. Set path (e.g. `/mnt/pool/videos`), enable "All dirs", add authorized network

**QNAP:**
1. Control Panel → Network & File Services → NFS Service → Enable
2. Shared Folders → Edit permissions → NFS host access

### Step 2: Test the NFS Mount on Your Server

```bash
# Install NFS client if needed
sudo apt install nfs-common       # Debian/Ubuntu
sudo yum install nfs-utils        # CentOS/RHEL

# Test mount
sudo mkdir -p /mnt/nas-videos
sudo mount -t nfs4 192.168.1.100:/volume1/videos /mnt/nas-videos

# Verify it works
ls /mnt/nas-videos
touch /mnt/nas-videos/test-file && rm /mnt/nas-videos/test-file
echo "NFS mount works!"
```

### Step 3: Migrate Existing Data

```bash
# Stop the app
docker compose down

# Copy existing data to NAS
rsync -avh --progress ./storage/ /mnt/nas-videos/

# Verify the copy
diff -r ./storage/db/ /mnt/nas-videos/db/
echo "Data migrated successfully"
```

### Step 4: Update Docker Compose

**Option A1: Use the NAS overlay file**

```bash
# Edit docker-compose.nas.yml with your NAS details
# Then start with both compose files:
docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d
```

**Option A2: Use a host mount (simpler)**

Add a permanent NFS mount to `/etc/fstab`:
```
192.168.1.100:/volume1/videos  /mnt/nas-videos  nfs4  rw,soft,timeo=300  0  0
```

Then mount and update `.env`:
```bash
sudo mount -a

# Update .env
echo "STORAGE_PATH=/mnt/nas-videos" >> .env

# Restart
docker compose up -d
```

### Step 5: Verify

```bash
# Check health
curl http://localhost:8000/api/health

# Check a video streams correctly
curl -I http://localhost:8000/api/videos  -H "X-API-Key: changeme"

# Check storage stats in the frontend at http://localhost:3000/settings
```

---

## Option B: SMB/CIFS Mount (Windows NAS or mixed environments)

### Step 1: Install CIFS Utils

```bash
sudo apt install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo mkdir -p /etc/samba
sudo tee /etc/samba/nas-credentials << 'EOF'
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
EOF
sudo chmod 600 /etc/samba/nas-credentials
```

### Step 3: Mount

```bash
sudo mkdir -p /mnt/nas-videos
sudo mount -t cifs //192.168.1.100/videos /mnt/nas-videos \
  -o credentials=/etc/samba/nas-credentials,uid=1000,gid=1000,file_mode=0664,dir_mode=0775
```

### Step 4: Make Permanent

Add to `/etc/fstab`:
```
//192.168.1.100/videos  /mnt/nas-videos  cifs  credentials=/etc/samba/nas-credentials,uid=1000,gid=1000,file_mode=0664,dir_mode=0775  0  0
```

Then follow Steps 3-5 from Option A.

---

## Option C: Direct Docker NFS Volume (No Host Mount)

Docker can mount NFS directly without a host mount point. This is what `docker-compose.nas.yml` does:

```bash
# Set your NAS details
export NAS_IP=192.168.1.100
export NAS_PATH=/volume1/videos

# Migrate data first (mount temporarily)
sudo mkdir -p /tmp/nas-mount
sudo mount -t nfs4 $NAS_IP:$NAS_PATH /tmp/nas-mount
rsync -avh --progress ./storage/ /tmp/nas-mount/
sudo umount /tmp/nas-mount

# Start with NAS overlay
docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d
```

---

## Performance Considerations

### SQLite over NFS

SQLite works over NFS but benefits from tuning:

1. **WAL mode** (already enabled by default) — best for NFS as it reduces write locks
2. **Busy timeout** — the app sets a 5-second busy timeout to handle NFS latency
3. **Journal size** — keep the WAL file small with periodic checkpoints

If you experience slow search queries over NFS, consider keeping the database on local SSD storage while storing videos on the NAS:

```bash
# .env — split storage
STORAGE_PATH=/mnt/nas-videos      # Videos and thumbnails on NAS
DATABASE_PATH=/opt/magpie/videos.db  # DB on local SSD (faster queries)
```

### Network Speed

- **1 Gbps**: Good enough for downloading and streaming 1080p
- **2.5/10 Gbps**: Recommended for 4K content or multiple simultaneous downloads
- **WiFi**: Not recommended for the server-to-NAS link (use wired ethernet)

### Recommended NAS Settings

- Enable **jumbo frames** (MTU 9000) on both NAS and server for better throughput
- Use **NFS v4.1** or later for better performance and security
- Enable **write caching** on the NAS for faster downloads
- Set up **RAID** for data protection (RAID 5 minimum for media storage)

---

## Backup Strategy

Since everything is under one directory tree:

```bash
# Full backup (database + all videos)
rsync -avh /mnt/nas-videos/ /backup/magpie/

# Database-only backup (metadata, tags, search index)
cp /mnt/nas-videos/db/videos.db /backup/magpie-db-$(date +%Y%m%d).db

# Automate with cron (daily DB backup)
echo "0 2 * * * cp /mnt/nas-videos/db/videos.db /backup/magpie-db-\$(date +\%Y\%m\%d).db" | crontab -
```

---

## Rollback

If you need to go back to local storage:

```bash
docker compose down

# Copy data back
rsync -avh /mnt/nas-videos/ ./storage/

# Remove NAS override from .env (or reset STORAGE_PATH)
echo "STORAGE_PATH=./storage" > .env

# Restart with local storage
docker compose up -d
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Permission denied" on NFS | Check NFS export permissions, ensure UID/GID match |
| Slow video streaming | Check network speed with `iperf3`, enable jumbo frames |
| SQLite "database is locked" | Increase busy_timeout, ensure only one writer process |
| Mount disappears after reboot | Add entry to `/etc/fstab` and run `sudo mount -a` |
| Docker can't create NFS volume | Install `nfs-common` on the Docker host |
| Videos play but thumbnails don't | Check file permissions in the thumbnails/ directory |
