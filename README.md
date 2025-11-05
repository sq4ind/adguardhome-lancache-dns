# AdGuardHome LanCache DNS Synchronizer

A production-ready synchronization tool that updates DNS rewrites in AdGuard Home to point specific services to your LanCache server. Designed for users running a local DNS server (AdGuard Home) in their LAN who want to leverage LanCache benefits without running additional DNS services.

## Features

- ✅ Automatic DNS rewrite synchronization from cache-domains repository
- ✅ Concurrent file downloads with configurable worker pool
- ✅ Batch processing with progress reporting
- ✅ Optional caching for fast recovery from failures
- ✅ Proper exit codes for orchestration and health checks
- ✅ Comprehensive error handling and logging
- ✅ Support for single services or all services
- ✅ Thread-safe operations
- ✅ Configurable retry strategies

## Installation and Configuration

### Requirements

- Docker installed on your system
- An existing AdGuard Home setup within your LAN
- AdGuard Home API access

### Quick Start

```bash
docker run --name adguard-lancache-dns -d \
  -e ADGUARD_USERNAME='admin' \
  -e ADGUARD_PASSWORD='password' \
  -e LANCACHE_SERVER='192.168.1.100' \
  -e ADGUARD_API='http://adguard.home:8080' \
  -e CRON_SCHEDULE='0 0 * * *' \
  -e ALL_SERVICES='true' \
  adguardhome-lancache-dns
```

### Environment Variables

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `ADGUARD_USERNAME` | Yes | - | AdGuard Home username | `admin` |
| `ADGUARD_PASSWORD` | Yes | - | AdGuard Home password | `password123` |
| `LANCACHE_SERVER` | Yes | - | LanCache server IP or hostname | `192.168.1.100` |
| `ADGUARD_API` | Yes | - | AdGuard Home API URL (include protocol and port) | `http://adguard.home:8080` |
| `CRON_SCHEDULE` | No | `0 0 * * *` | Cron schedule for periodic updates (runs daily at midnight) | `0 */6 * * *` |
| `ALL_SERVICES` | No | `false` | Enable all available services (true/false) | `true` |
| `SERVICE_NAMES` | No | - | Comma-separated list of services to enable | `wsus,steam,epicgames,xboxlive` |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) | `DEBUG` |
| `MAX_WORKERS` | No | `3` | Number of concurrent download workers | `5` |
| `BATCH_SIZE` | No | `100` | Number of rewrites between progress logs | `50` |
| `CACHE_FILE` | No | - | Path to cache file for DNS rewrites (enables caching) | `/var/cache/dns_rewrites.json` |

**Note**: Either `ALL_SERVICES=true` OR `SERVICE_NAMES` must be specified, but not both undefined.

### Available Services

The tool supports all services from the [cache-domains](https://github.com/uklans/cache-domains) repository, including:

arenanet, blizzard, bsg, cityofheroes, cod, daybreak, epicgames, frontier, neverwinter, nexusmods, nintendo, origin, pathofexile, renegadex, riot, rockstar, sony, square, steam, teso, test, uplay, warframe, wargaming, wsus, xboxlive

### Docker Compose Example

```yaml
version: '3.8'

services:
  adguard-lancache-dns:
    image: adguardhome-lancache-dns:latest
    container_name: adguard-lancache-dns
    restart: unless-stopped
    environment:
      - ADGUARD_USERNAME=admin
      - ADGUARD_PASSWORD=your_password
      - LANCACHE_SERVER=192.168.1.100
      - ADGUARD_API=http://adguard.home:8080
      - CRON_SCHEDULE=0 0 * * *
      - ALL_SERVICES=true
      - LOG_LEVEL=INFO
      - MAX_WORKERS=3
      - BATCH_SIZE=100
      - CACHE_FILE=/var/cache/dns_rewrites.json
    volumes:
      - dns_cache:/var/cache

volumes:
  dns_cache:
```

## How It Works

1. **Fetch Service Metadata**: Retrieves list of services from the cache-domains repository
2. **Download Domain Lists**: Concurrently downloads domain lists for selected services using configurable worker pool
3. **Process & Cache**: Converts domains to AdGuard Home rewrite format and optionally caches results
4. **Update DNS Rewrites**: Batch-processes rewrites to AdGuard Home (added/updated/skipped tracking)
5. **Report Results**: Logs summary of added, updated, and skipped rewrites

### Concurrency Control

- **MAX_WORKERS**: Controls number of concurrent downloads (default: 3)
  - Lower values: Less network load, slower downloads
  - Higher values: Faster downloads, more network load
- **BATCH_SIZE**: Progress logging frequency (default: 100 rewrites)
  - Prevents log spam while showing progress on large updates

### Caching

Enable caching to speed up recovery from failures:

```bash
-e CACHE_FILE=/var/cache/dns_rewrites.json
```

When enabled, DNS rewrites are saved after download. Useful for:
- Quick re-runs after temporary failures
- Testing AdGuard Home connectivity issues
- Avoiding re-downloads during development

## Advanced Usage

### Performance Tuning

For slower networks with DNS resolution issues:

```bash
docker run ... \
  -e MAX_WORKERS=2 \
  -e LOG_LEVEL=DEBUG \
  adguardhome-lancache-dns
```

For fast networks with stable connectivity:

```bash
docker run ... \
  -e MAX_WORKERS=10 \
  -e BATCH_SIZE=500 \
  adguardhome-lancache-dns
```

### Health Checks

Add health check to Docker Compose:

```yaml
healthcheck:
  test: [ "CMD", "python", "/app/UpdateAdGuardDNSRewrites.py" ]
  interval: 6h
  timeout: 30s
  retries: 2
  start_period: 30s
```

### Kubernetes Deployment

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: adguard-lancache-dns
spec:
  schedule: "0 0 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sync
            image: adguardhome-lancache-dns:latest
            env:
            - name: ADGUARD_USERNAME
              valueFrom:
                secretKeyRef:
                  name: adguard-credentials
                  key: username
            - name: ADGUARD_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: adguard-credentials
                  key: password
            - name: LANCACHE_SERVER
              value: "192.168.1.100"
            - name: ADGUARD_API
              value: "http://adguard.home:8080"
            - name: ALL_SERVICES
              value: "true"
          restartPolicy: OnFailure
```

## Exit Codes

- `0`: Successful execution
- `1`: Configuration error or runtime failure

## Troubleshooting

### DNS Resolution Errors

If you see `NameResolutionError` messages:

1. Verify container DNS configuration:
   ```bash
   docker run --dns=8.8.8.8 ... adguardhome-lancache-dns
   ```

2. Check AdGuard Home DNS settings:
   ```bash
   docker exec adguard-lancache-dns nslookup raw.githubusercontent.com
   ```

3. Increase retry attempts by checking logs:
   ```bash
   docker logs -f adguard-lancache-dns
   ```

### Connection Failures

Enable debug logging:

```bash
docker run ... -e LOG_LEVEL=DEBUG adguardhome-lancache-dns
```

### Slow Synchronization

Adjust concurrency:

```bash
docker run ... -e MAX_WORKERS=5 adguardhome-lancache-dns
```

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/improvement`
3. Commit changes: `git commit -am 'Add improvement'`
4. Push to branch: `git push origin feature/improvement`
5. Submit a Pull Request

## License

This project is available under the [MIT License](LICENSE). You are free to fork, modify, and use it in any way you see fit.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.