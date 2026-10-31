# Publishing generated Pythios apps

Pythios publishes each successful coding-agent result automatically. The
project's existing six-character lowercase alphanumeric ID remains its public
identifier, so a project such as `a1b2c3` is available at:

```
https://app.pythios.xyz/a1b2c3
```

## How it works

`POST /generate` calls `ai-core/main.py`, which calls `ProjectBuilder`. After
the coding agent has finished, the builder verifies that its workspace contains
a complete `index.html`, copies the artifact into an immutable version on the
configured data volume, and atomically swaps a manifest for that project ID.
The old manifest remains active if generation, validation, copying, or the
manifest write fails.

The public route serves a minimal shell. The generated document is loaded from
an internal asset route in a sandboxed iframe with `allow-scripts`,
`allow-forms`, and `allow-modals` only. It never receives `allow-same-origin`
or top-level-navigation permission, so generated JavaScript cannot inherit the
Pythios application's origin, cookies, or browser storage.

Existing legacy directories in `published/<project-id>/` remain readable. The
next successful generation moves a project onto the atomic versioned layout.

## Production configuration

The repository does not contain a Netlify routing rule for this subdomain.
Pointing `app.pythios.xyz` directly at the existing Render backend keeps the
main Netlify builder site separate and avoids a Netlify catch-all rewrite that
would break the builder's own routes.

In Render, add `app.pythios.xyz` as a custom domain for the existing backend
service, then create this DNS record (or use the exact target Render displays
while adding the domain):

```
Type: CNAME
Name: app
Value: pythois.onrender.com
```

### Persistent-disk deployment

Set these Render environment variables when using a persistent disk:

```
PYTHIOS_PUBLIC_APP_URL=https://app.pythios.xyz
PYTHIOS_DATA_DIR=/var/data/pythios
```

Attach a persistent Render disk to the backend service at `/var/data`. A local
filesystem or Render's normal service filesystem is ephemeral: projects can
disappear after a redeploy or replacement instance if no disk is attached.
Render currently offers persistent disks only to paid eligible services, so
this is the only required production cost beyond the existing service; exact
disk and plan pricing is selected in the Render dashboard.

Use one backend instance with this Render disk configuration. Render disks are
attached to a single service instance and disable zero-downtime deploys; the
filesystem lock additionally protects concurrent writers on a shared POSIX disk
in local or self-managed deployments.

### No-disk deployment (GitHub archive)

Free Render services cannot attach a persistent disk. In that configuration,
the local filesystem is only a cache and the durable published version is kept
in the connected GitHub repository. Set these Render environment variables:

```
PYTHIOS_PUBLIC_APP_URL=https://app.pythios.xyz
GITHUB_TOKEN=<fine-grained token with Contents: Read and write>
GITHUB_REPOSITORY=Advaith0611/Delphi
GITHUB_BRANCH=main
GITHUB_ARCHIVE_PATH=generated-projects
PYTHIOS_REQUIRE_GITHUB_ARCHIVE=true
```

Remove `PYTHIOS_DATA_DIR=/var/data/pythios` (or leave it: the backend safely
falls back to temporary storage when `/var/data` is unavailable). Each
successful generation uploads an immutable version first, then atomically
updates `generated-projects/<project-id>/.published.json`. After a Render
restart the public route reads that manifest and serves the version through the
same sandboxed iframe. The repository must remain available to Render; private
repositories require the token for both writing and reading.

When a user regenerates an existing project after a Render restart, the backend
restores that published version from GitHub into its temporary workspace before
running the coding agent. The existing six-character project ID and public URL
are retained.

After deploying, verify both:

```
curl -I https://app.pythios.xyz/a1b2c3
curl -I -H 'Sec-Fetch-Dest: iframe' https://app.pythios.xyz/__published/a1b2c3/index.html
```

The first response is the sandbox shell; the second is the generated document
when requested by an iframe. The internal `__published` HTML URL rejects
top-level navigation, so it cannot become an unsandboxed public execution
route.
