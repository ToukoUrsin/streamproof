# AWS deployment route — prepared, not yet executed

OpenCV competition eligibility requires meaningful AWS use. The local app does **not** satisfy that requirement by itself. This repository provides a container whose complete OpenCV pipeline can execute on an AWS runtime. Set a runtime label only after it is true. Record the account/region/service and a live `GET /api/status` verification in the submission evidence when deployment is done; never commit credentials.

A small Amazon Lightsail Linux VM with a persistent disk is a practical judge-demo deployment. Run the image on that VM, mount a durable `/data` volume, bind the container only to localhost, and terminate HTTPS through a reverse proxy. Use a `STREAMPROOF_TOKEN` provided separately to judges. This makes AWS responsible for image ingestion, actual CPU vision processing, durable evidence storage and authenticated exports rather than a cosmetic integration.

```sh
# Build after verifying the pinned wheel exists for the VM architecture.
docker build -t streamproof:0.1 .
docker volume create streamproof-data
# Put STREAMPROOF_TOKEN in a private env file (mode 600); do not commit it.
docker run -d --name streamproof --restart unless-stopped \
  --env-file /secure/path/streamproof.env \
  -e STREAMPROOF_RUNTIME='AWS Lightsail' \
  -v streamproof-data:/data -p 127.0.0.1:8080:8080 streamproof:0.1
```

After TLS is configured, verify the authentic status response reports OpenCV 5.0.0. Exercise upload → baseline → control change → human review → export remotely, then store the measured response and test date. Test unauthenticated image and export requests return 401. Keep backups of the persistent volume. Restrict operator access; the prototype is single-workspace and should not ingest public sensitive submissions.

No infrastructure has been provisioned by these files. Docker build and Linux execution must be checked on the actual target before claiming deployment success. ECR/ECS with an encrypted EFS volume is a viable alternative, but is unnecessary complexity for a small demonstration. Do not use ephemeral filesystem-only services without adding durable storage.
