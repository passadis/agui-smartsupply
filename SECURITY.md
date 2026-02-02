# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

The AGUI SmartSupply team takes security bugs seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report a Security Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing the maintainers or using GitHub's private vulnerability reporting feature:

1. **Via GitHub Security Advisory**
   - Go to the [Security tab](https://github.com/passadis/agui-smartsupply/security) of this repository
   - Click "Report a vulnerability"
   - Fill in the details of the vulnerability

2. **Via Email**
   - Send an email with the details to the project maintainers
   - Include as much information as possible (see below)

### What to Include in Your Report

To help us better understand the nature and scope of the issue, please include as much of the following information as possible:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

### What to Expect

After you submit a vulnerability report:

1. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 3 business days
2. **Assessment**: We will investigate and validate the vulnerability
3. **Updates**: We will send you regular updates about our progress
4. **Resolution**: Once the vulnerability is fixed, we will notify you
5. **Disclosure**: We will work with you to determine an appropriate disclosure timeline

### Security Update Process

1. The security issue is received and assigned to a primary handler
2. The problem is confirmed and affected versions are determined
3. Code is audited to find any similar problems
4. Fixes are prepared for all supported versions
5. New versions are released and announcements are made

## Security Best Practices for Users

### Azure Credentials

- **Never commit** Azure credentials, API keys, or connection strings to the repository
- Use environment variables or Azure Key Vault for sensitive configuration
- Rotate credentials regularly
- Use managed identities when possible
- Follow the principle of least privilege

### Docker Security

- Keep Docker images up to date
- Use official base images when possible
- Don't run containers as root unless necessary
- Scan images for vulnerabilities regularly

### Network Security

- Use HTTPS/TLS for all external communications
- Implement proper firewall rules for Azure SQL and other services
- Use Azure Virtual Networks when appropriate
- Enable Azure SQL firewall rules to restrict access

### Data Protection

- Encrypt sensitive data at rest and in transit
- Implement proper access controls for Azure Blob Storage
- Use SAS tokens with appropriate expiration times
- Regularly audit access logs

### Dependencies

- Keep all dependencies up to date
- Regularly check for security advisories
- Use tools like `pip-audit` or `safety` to scan Python dependencies
- Review dependency changes before updating

## Known Security Considerations

### Azure OpenAI

- API keys should be stored securely
- Implement rate limiting to prevent abuse
- Monitor usage for anomalies
- Be aware of data residency requirements

### Database Security

- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Encrypt connection strings
- Regular backup and disaster recovery planning

### MCP Server Security

- Validate all input from MCP clients
- Implement proper authentication if exposing to untrusted networks
- Use HTTPS in production
- Rate limit API requests

## Disclosure Policy

- We will coordinate vulnerability disclosure with you
- Security advisories will be published on GitHub Security Advisories
- We will credit researchers who responsibly disclose vulnerabilities (unless you prefer to remain anonymous)

## Comments on This Policy

If you have suggestions on how this process could be improved, please submit a pull request or open an issue.

## Security Hall of Fame

We recognize and thank the following security researchers for their responsible disclosure:

- (None yet - be the first!)

---

Thank you for helping keep AGUI SmartSupply and its users safe!
