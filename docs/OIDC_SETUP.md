# OIDC Authentication Setup

This document explains how to configure OpenID Connect (OIDC) authentication for the Corkboard admin site using `social-auth-app-django`.

## Overview

Corkboard now supports OIDC authentication for accessing the Django admin interface. This allows you to use any OIDC-compliant identity provider (such as Auth0, Keycloak, Okta, Google, etc.) for secure admin access.

## Configuration

### Required Environment Variables

To enable OIDC authentication, you need to set the following environment variables:

```bash
# OIDC Provider Configuration
OIDC_ENDPOINT=https://your-provider.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

### Environment Variable Details

- **OIDC_ENDPOINT**: The OIDC discovery endpoint URL. This is typically the base URL of your identity provider followed by `/.well-known/openid-configuration`. For example:
  - Auth0: `https://your-tenant.auth0.com/.well-known/openid-configuration`
  - Keycloak: `https://your-domain/auth/realms/your-realm/.well-known/openid-configuration`
  - Google: `https://accounts.google.com/.well-known/openid-configuration`

- **OIDC_CLIENT_ID**: The client ID provided by your OIDC provider when you register your application.

- **OIDC_CLIENT_SECRET**: The client secret provided by your OIDC provider. Keep this secure and never commit it to version control.

## Setup Steps

### 1. Register Your Application with Your OIDC Provider

You'll need to register Corkboard as an application with your OIDC provider. During registration, you'll need to provide:

- **Redirect URI**: `https://your-domain.com/complete/oidc/` (replace `your-domain.com` with your actual domain)
- **Allowed Scopes**: At minimum, you'll need `openid`, `email`, and `profile`

### 2. Configure Environment Variables

Set the three required environment variables with the values from your OIDC provider:

```bash
export OIDC_ENDPOINT="https://your-provider.com/.well-known/openid-configuration"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
```

### 3. Database Migration

The OIDC integration requires database tables for storing social authentication data. These have already been migrated if you've run the latest migrations:

```bash
python manage.py migrate
```

### 4. Test the Integration

1. Start the development server:
   ```bash
   just serve
   ```

2. Navigate to the admin login page: `http://localhost:8000/admin/`

3. You should see a link to "Login with OIDC" or similar, depending on your provider's configuration.

4. Click the link and you'll be redirected to your OIDC provider for authentication.

5. After successful authentication, you'll be redirected back to the Corkboard admin interface.

## How It Works

### Authentication Flow

1. User clicks "Login with OIDC" on the admin page
2. User is redirected to the OIDC provider's login page
3. User authenticates with their credentials
4. OIDC provider redirects back to Corkboard with an authorization code
5. Corkboard exchanges the code for ID and access tokens
6. Corkboard creates or updates the user in the local database
7. User is logged in and redirected to the admin interface

### User Creation

When a user logs in via OIDC for the first time:
- A new Django user is created automatically
- The user's email and name are populated from the OIDC provider
- The user is granted staff status (required to access admin)
- No password is set (authentication is always via OIDC)

### Dual Authentication

The system supports both OIDC and traditional Django authentication:
- OIDC authentication (recommended for production)
- Django's built-in username/password authentication (fallback)

## URLs

The following authentication URLs are available:

- **Admin Login**: `/admin/login/`
- **OIDC Login**: `/login/oidc/`
- **OIDC Callback**: `/complete/oidc/`
- **Logout**: `/admin/logout/`

## Customization

### Custom User Pipeline

You can customize how users are created and updated by modifying the `SOCIAL_AUTH_PIPELINE` setting in `config/settings.py`. The default pipeline is:

```python
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
```

You can add custom pipeline functions to implement additional logic, such as:
- Auto-granting admin/staff permissions based on OIDC groups
- Custom username generation
- Additional user profile fields

### Additional Scopes

To request additional scopes from your OIDC provider, modify the `SOCIAL_AUTH_OIDC_SCOPE` setting in `config/settings.py`:

```python
SOCIAL_AUTH_OIDC_SCOPE = ["openid", "email", "profile", "groups"]
```

## Security Considerations

1. **Always use HTTPS in production** - OIDC tokens should never be transmitted over HTTP
2. **Keep OIDC_CLIENT_SECRET secure** - Use environment variables or a secrets manager
3. **Configure allowed redirect URIs** properly in your OIDC provider
4. **Review user permissions** - Consider implementing a custom pipeline to control admin access
5. **Session security** - Review Django's session configuration for your security requirements

## Troubleshooting

### "Invalid redirect URI" error
- Verify the redirect URI in your OIDC provider matches exactly: `https://your-domain.com/complete/oidc/`
- Ensure you're using the correct protocol (http vs https)

### "Missing scopes" error
- Verify your OIDC provider allows the requested scopes (openid, email, profile)
- Check that your client application is authorized for these scopes

### User is not staff/admin
- The default pipeline creates users but doesn't grant staff status automatically
- You'll need to manually grant staff status via Django admin or implement a custom pipeline

### Authentication works but can't access admin
- Verify the user has `is_staff=True` and appropriate permissions
- Check Django's permission system: `python manage.py shell` → `User.objects.get(email='...').is_staff`

## References

- [Python Social Auth Documentation](https://python-social-auth.readthedocs.io/)
- [Django Social Auth Documentation](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html)
- [OpenID Connect Specification](https://openid.net/connect/)
