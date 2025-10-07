# blueos-net-shaper

BlueOS extension that allows simulating packet loss, latency, and bandwidth limitation on the host (Raspberry Pi) without installing anything on the HostOS.

## Build

### Multi-Architecture Build (Recommended)

To support Raspberry Pi 4, 5, and desktops, build for multiple architectures:

1. Create a buildx builder (first time only):

```bash
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```

2. Build and push for multiple platforms:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t rafaellehmkuhl/blueos-net-shaper:latest \
  --push .
```

Or use the provided build script: `./build.sh`

### Single Architecture Build (Local Testing)

For local testing on your current architecture:

```bash
docker build -t rafaellehmkuhl/blueos-net-shaper:latest .
```

## Deploy on BlueOS
- Use the `manifest.json` pointing to the image.
- The extension needs to run with `network: host` and `cap_add: ["NET_ADMIN"]`.
- If BlueOS doesn't allow `cap_add`, set `privileged: true` (for testing only).

## Usage
- API exposed on `:8080` inside the container. BlueOS typically provides the extension via URL/iframe in the dashboard.
- Examples:
  - Limit outbound to 512 kbit: `POST /bandwidth/out/512`
  - 30% outbound packet loss: `POST /loss/out/30`
  - 20% inbound packet loss: `POST /loss/in/20`
  - Clear everything: `POST /bandwidth/clear`

## Supported Architectures

This extension is built for multiple architectures:
- **linux/amd64** - Desktop computers (Intel/AMD)
- **linux/arm64** - Raspberry Pi 4, 5 with 64-bit OS
- **linux/arm/v7** - Raspberry Pi 3, 4 with 32-bit OS

## Important Notes
- **Nothing is installed on the HostOS**: all tools (tc, ip, iptables) are inside the container. However, the container needs permission to manipulate the host's network stack.
- **IFB:** for ingress (inbound) loss, `ifb` is required — the container uses `modprobe ifb` and creates `ifb0`. On some hosts, loading kernel modules from the container requires extra capabilities; if it doesn't work, only egress simulation will be available.
- **Security:** protect API access; don't expose to untrusted networks.
- **Test first:** run on a lab Pi before applying to production equipment.

