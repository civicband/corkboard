# Corkboard

Corkboard is the "front door" of https://civic.band. All the code that controls the experience of visiting the CivicBand homepage or the municipality sites lives in this repo.

The core of Corkboard is a django app with two main purposes:

1. Serving https://civic.band, the homepage and the site search pages
2. Serving each CivicBand site, which is rendered as a Datasette site on top of each municipality's SQLite DB.

We welcome contributions, please check out our [contributor's guide](https://github.com/civicband/corkboard/blob/main/CONTRIBUTING.md)
