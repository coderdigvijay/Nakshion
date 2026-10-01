# Brevo Email Delivery

## Sender verification
- `noreply@yourdomain.com` won't deliver without domain DNS verification
- Without a custom domain, use the Brevo account signup email as sender
- Current sender: `coderdigvijay@gmail.com` (Brevo signup email)
- When custom domain is ready, add DNS records in Brevo → Settings → Senders & Domains

## Email best practices (avoid spam)
- Include both HTML and plain text versions
- Use proper sender name ("Nakshion" not generic)
- No ALL CAPS in subject lines
- Include unsubscribe/ignore notice in footer
- Use `X-Mailin-Tag` header for categorization
