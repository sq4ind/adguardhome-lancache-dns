# AdGuardHome-lancache-dns

## Introduction

AdGuardHome-lancache-dns is a synchronization tool designed to update DNS entries for specific services for the lancache server as rewrites to the AdGuardHome DNS server. It serves users who already have a running local DNS server (AdGuard Home) in their LAN and wish to avoid running an additional lancache-dns container. This project simplifies the integration of lancache server benefits without the necessity for additional DNS services.

## Installation and Configuration

### Requirements

- Docker installed on your system
- An existing AdGuard Home setup within your LAN

### Setup

To start using AdGuardHome-lancache-dns, utilize the following Docker command:

```bash
docker run --name=adguard-lancache-dns -d \
  -e ADGUARD_USERNAME='admin' \
  -e ADGUARD_PASSWORD='password' \
  -e LANCACHE_SERVER='ip_address' \
  -e ADGUARD_API='adguard_api' \
  -e CRON_SCHEDULE="0 0 * * *" \
  -e ALL_SERVICES=false \
  -e SERVICE_NAMES='steam' \
  adguardhome-lancache-dns
```

#### Environment Variables

| Variable         | Description                        | Required  | Default         | Example                         |
|------------------|------------------------------------|-----------|-----------------|---------------------------------|
| ADGUARD_USERNAME | Username for AdGuard Home          | Yes       |                 | ADGUARD_USERNAME=admin          |
| ADGUARD_PASSWORD | Password for AdGuard Home          | Yes       |                 | ADGUARD_PASSWORD=admin          |
| LANCACHE_SERVER  | IP address of your lancache server | Yes       |                 | LANCACHE_SERVER=192.168.1.1     |
| ADGUARD_API      | API URL for AdGuard Home           | Yes       |                 | ADGUARD_API=http://fw.home:8080 |
| CRON_SCHEDULE    | Schedule for syncing DNS entries   | No        | "0 0 * * *"     | CRON_SCHEDULE="* * * * *" |      |
| ALL_SERVICES     | Sync all services (true/false)     | No        |                 | ALL_SERVICES=true |
| SERVICE_NAMES    | Services to sync DNS entries for   | No*       |                 | SERVICE_NAMES=wsus,epicgames,steam,xboxlive |

*Note: Either `ALL_SERVICES` must be set to true, or `SERVICE_NAMES` must be specified.

### How It Works

Upon configuring and initiating the container with the required environment variables, AdGuardHome-lancache-dns will automatically sync DNS entries for the designated services to your AdGuard Home installation. This process is governed by the `CRON_SCHEDULE` setting, allowing for periodic updates without manual intervention.

## Contributing

We welcome contributions! For enhancements or fixes, please submit an issue or pull request on GitHub. Your contributions help improve AdGuardHome-lancache-dns for everyone.

## License

This project is available under the [MIT License](LICENSE). You are free to fork, modify, and use it in any way you see fit.
