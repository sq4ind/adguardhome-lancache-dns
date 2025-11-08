# Security Policy

## Overview

This project takes security seriously. We are committed to maintaining the integrity and security of the AdGuardHome LanCache DNS Synchronizer codebase and all released artifacts.

## Security Scanning

All Docker images are automatically scanned for known vulnerabilities using **Trivy**, an open-source vulnerability scanner by Aqua Security. Security scanning is performed as part of our CI/CD pipeline on every release.

### Scan Coverage

- **Vulnerability Types**: OS packages, application dependencies, and Python packages
- **Severity Levels**: CRITICAL, HIGH, MEDIUM, LOW, and UNKNOWN
- **Platforms**: All supported architectures (linux/amd64, linux/arm64, linux/arm/v7)
- **Frequency**: Automatic on every tagged release

### Accessing Scan Results

Vulnerability scan results are available in multiple locations:

1. **GitHub Security Tab**
   - Navigate to your repository → **Security** → **Code scanning alerts**
   - View all detected vulnerabilities with severity levels and remediation guidance

2. **GitHub Actions Artifacts**
   - Download detailed JSON reports from workflow runs
   - File: `trivy-scan-report`
   - Contains full vulnerability information including CVE IDs and fix recommendations

3. **Release Notes**
   - Security information is included in each release
   - Links to security alerts are provided for transparency

## Supported Versions

| Version | Status | Security Updates |
|---------|--------|------------------|
| Latest (main branch) | Active | ✅ Yes |
| Released Tags | Active | ✅ Yes |

## Reporting Security Issues

If you discover a security vulnerability in this project, please do **NOT** open a public GitHub issue. Instead:

### Private Disclosure Process

1. **Email us** at: (add your preferred security contact email or point to your organization's security policy)
2. **Include details**:
   - Description of the vulnerability
   - Steps to reproduce (if applicable)
   - Potential impact
   - Suggested fix (if you have one)

3. **Expected response timeline**:
   - Acknowledgment: Within 48 hours
   - Initial assessment: Within 1 week
   - Fix or mitigation plan: Within 2 weeks
   - Public disclosure: Coordinated after a fix is available

### Security Advisory Process

Once a security issue is fixed:
1. A security advisory will be published on GitHub
2. The fix will be released as a patch version
3. Users will be notified through GitHub's security alert system
4. Public credit will be given to the reporter (unless they prefer anonymity)

## Keeping Your System Secure

### Best Practices

1. **Use Official Images**: Always pull from official registries:
   - GitHub Container Registry: `ghcr.io/sq4ind/adguardhome-lancache-dns`
   - Docker Hub: Check for official distribution

2. **Verify Image Signatures**: Use Docker Content Trust where available

3. **Keep Updated**: Regularly update to the latest version:
   ```bash
   docker pull ghcr.io/sq4ind/adguardhome-lancache-dns:latest
   ```

4. **Run with Minimal Privileges**: Follow Docker security best practices
   ```bash
   docker run --read-only --cap-drop=ALL --security-opt=no-new-privileges
   ```

5. **Use Network Policies**: Restrict container network access as needed

6. **Monitor Logs**: Regularly review container and application logs for suspicious activity

### Dependency Security

This project's dependencies are:
- Automatically scanned for vulnerabilities
- Updated regularly to include security patches
- Specified in `requirements.txt` (Python) and `Dockerfile` (base image)

## Base Image Security

All Docker images are based on Alpine Linux, which is:
- Lightweight and minimal (reduces attack surface)
- Actively maintained with security updates
- Regularly scanned for known vulnerabilities

**Current Base Image**: Alpine Linux 3.22 (or latest stable)

## Container Security Features

### Read-Only Filesystem
Consider running containers with a read-only root filesystem where possible.

### Capability Dropping
Unnecessary Linux capabilities are dropped to minimize potential privilege escalation risks.

### Non-Root User
The application runs as a non-root user when possible to limit damage from potential exploits.

## Security Updates Timeline

| Update Type | Frequency | Priority |
|-------------|-----------|----------|
| Critical (CVSS 9.0-10.0) | As needed | Immediate |
| High (CVSS 7.0-8.9) | Within 1 week | High |
| Medium (CVSS 4.0-6.9) | Within 2 weeks | Medium |
| Low (CVSS 0.1-3.9) | Next scheduled release | Low |

## Known Issues and Limitations

- Alpine Linux packages may occasionally have minor vulnerabilities; these are typically addressed quickly by the Alpine security team
- Build tools and development dependencies are not included in the final image, reducing the attack surface
- Some third-party dependencies may have unpatched vulnerabilities; these are clearly documented

## Security Checklist for Users

- [ ] Always pull images from official registries
- [ ] Keep your Docker daemon and container runtime updated
- [ ] Regularly update your deployed containers
- [ ] Monitor GitHub security alerts for this repository
- [ ] Review vulnerability scan reports after each update
- [ ] Follow container security best practices
- [ ] Implement network segmentation in your infrastructure
- [ ] Enable container runtime security monitoring

## Compliance and Standards

This project follows:
- **Docker Best Practices**: Official Docker security guidelines
- **OWASP Container Security**: Industry standard practices
- **CIS Docker Benchmark**: Configuration security standards

## Questions or Concerns?

For security-related questions (non-disclosure):
- Open a discussion in GitHub Discussions
- Reference existing security documentation
- Check GitHub Security Advisories

For security vulnerabilities:
- Use the private disclosure process outlined above
- Do not publicly disclose before a fix is available

## Changelog

### Version 1.0 (2025-11-08)
- Implemented automated vulnerability scanning with Trivy
- Added SARIF format reporting to GitHub Security tab
- Established security advisory process
- Documented security best practices

---

**Last Updated**: 2025-11-08

For the latest information, visit the [GitHub repository](https://github.com/sq4ind/adguardhome-lancache-dns).