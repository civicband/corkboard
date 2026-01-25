# Caddyfile Changes for Django Homepage

## Required Change

Update the `civic.band` block in the Caddyfile to route to Django instead of sites_datasette:

### Before
```
civic.band {
    import subdomain-log civic.band
    import block_brazilians
    root * static
    route {
        file_server /how.html
        file_server /why.html
        file_server /privacy.html
        file_server /rss.xml
        reverse_proxy * 127.0.0.1:40001 127.0.0.1:40002 {
            import health-proxy
        }
    }
}
```

### After
```
civic.band {
    import subdomain-log civic.band
    import block_brazilians
    root * static
    route {
        file_server /how.html
        file_server /why.html
        file_server /privacy.html
        file_server /rss.xml
        reverse_proxy * 127.0.0.1:8000 127.0.0.1:8001 {
            import health-proxy
        }
    }
}
```

## Rollback

To rollback, revert the Caddyfile change to use ports 40001/40002.

## Verification

After deployment:
1. Visit https://civic.band/
2. Verify homepage loads with search/filter/map
3. Verify subdomains still work (e.g., https://berkeley.ca.civic.band)
