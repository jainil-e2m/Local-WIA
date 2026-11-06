# SOP: FastAPI Backend Project Structure

Internal Technical Reference  —  Team Minu

### Purpose

This SOP defines the standard file and folder structure for FastAPI backend projects in this team. The goal is to keep projects consistent, easy to review, easy to onboard into, and simple enough for associates and interns to follow without unnecessary complexity.

## 1. Standard Backend Directory Structure

All backend code should live inside a dedicated backend/ folder in the repository.

```text
repo-root/
├── backend/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── auth.py
│   │   └── users.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   ├── helpers.py
│   │   │   └── exceptions.py
│   │   ├── users/
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   ├── helpers.py
│   │   │   └── validators.py
│   │   └── shared/
│   │       ├── __init__.py
│   │       ├── constants.py
│   │       └── common.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── auth.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── session.py
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── requests.py
│   │       └── responses.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── dates.py
│   │   ├── strings.py
│   │   └── security.py
│   │
│   ├── sql/
│   │   ├── schema/
│   │   ├── migrations/
│   │   ├── seeds/
│   │   └── README.md
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── fixtures/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── integration/
│   │   └── smoke/
│   │
│   ├── scripts/
│   │   ├── bootstrap/
│   │   ├── maintenance/
│   │   └── data/
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── queue.py
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   └── notifications.py
│   │   └── README.md
│   │
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── README.md
│   │
│   ├── app.py
│   ├── db.py
│   ├── config.py
│   ├── .env.example
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── requirements.txt
│   └── README.md
│
└── other-repo-files...
```

## 2. Folder-by-Folder Purpose

### routes/

Contains API endpoint files only.
Use this folder for:

- grouping API endpoints by domain or feature
- keeping route registration organized
- separating external API exposure from internal business logic

Rule: Route files should map clearly to feature areas such as auth.py, users.py, orders.py, health.py.
Do not place business logic, database access logic, or utility-heavy processing directly in this folder.

### services/

Contains business logic and service-level organization. This is the main place where feature logic should be compartmentalized.

#### Recommended service structure

Use subfolders inside services/ when a feature has more than one logical responsibility.
Example service subfolders:

- services/auth/
- services/users/
- services/payments/
- services/shared/

Within each service subfolder, use a simple internal split:

- service.py — primary feature service layer
- helpers.py — supporting internal helper logic specific to that service
- validators.py — feature-specific validation helpers if needed
- exceptions.py — service-specific exception definitions if needed

#### When to create a subfolder in services/

Create a service subfolder when:

- the feature is large enough to have multiple responsibilities
- multiple files would otherwise clutter the top-level services/ folder
- the feature is expected to grow

#### When not to create a subfolder

Do not create subfolders for very small or temporary features. In those cases, a single service file is enough.
Goal: keep services/ organized, but avoid over-engineering.

### models/

Contains data model definitions used by the backend. This folder is required so that data structures are not scattered randomly across routes or services.

A balanced structure inside models/ is:

- models/domain/ — business/domain-level models
- models/db/ — database-facing models or table/entity representations
- models/schemas/ — API request/response schemas or transport models

#### Notes on models/

- Keep model placement consistent across the project.
- Do not mix all model types into one large file.
- Do not duplicate the same concept in multiple places without a reason.
- If the project is small, these can remain as a few files only. If it grows, expand carefully.

### utils/

Contains reusable general-purpose helper functions. Use this folder for utilities that are generic, reusable across multiple features, and not tied to one specific service.

Examples include date helpers, string helpers, formatting helpers, or common security helpers.
Rule: if helper logic is feature-specific, keep it inside that feature's service folder instead of utils/.

### sql/

Contains all database-related SQL assets. This folder should remain the single source of truth for database change history and SQL assets.

Recommended internal structure:

- schema/ — initial database structure definitions
- migrations/ — migration files
- seeds/ — seed or reference data scripts
- README.md — explaining how this project handles database changes

### tests/

Contains all automated tests relevant to the backend.

Recommended structure:

- fixtures/ — reusable test setup data and helpers
- routes/ — endpoint-level tests
- services/ — business-logic tests
- integration/ — cross-component or database-connected tests
- smoke/ — minimal high-value system checks
- conftest.py — shared test configuration

#### Test folder rules

- Test structure should roughly mirror the production structure.
- Only include tests that are relevant and maintained.
- Do not keep abandoned, placeholder, duplicate, or dead tests in the repository.
- A small number of reliable tests is better than a large number of meaningless tests.
- If a feature has no realistic value in being tested, do not create a test just for appearance.
- The repo should contain relevant tests only.

### scripts/

Contains one-off or operational scripts that support development or maintenance. This folder should not become a dumping ground. If a script becomes a core part of the product workflow, consider whether it belongs elsewhere.

Recommended internal structure:

- bootstrap/ — local setup or initialization scripts
- maintenance/ — maintenance tasks
- data/ — import/export or data handling scripts

### workers/

Contains background job and worker-related setup. Use this folder when the backend requires asynchronous job processing using Redis/RQ. Keep worker-specific concerns here instead of mixing them into routes or generic services.

Recommended structure:

- queue.py — queue setup and worker bootstrap references
- jobs/ — individual job groupings by feature
- README.md — to document worker startup and conventions

### logging/

Contains logging setup configuration. This prevents logging setup from being scattered across the codebase.

Recommended contents:

- config.py — logging configuration setup
- README.md — for log conventions if needed

## 3. Required Root-Level Backend Files

### app.py

This is the FastAPI application entrypoint. It should act as the central application bootstrap file and should be the single clear place where the backend application starts.

### db.py

This is the database entrypoint. It should contain the database connection setup, pooling setup, and shared database access bootstrap logic for the project.

### config.py

This file should define how application configuration is loaded and accessed. It should act as the central source for:

- environment-driven settings
- app-level configuration values
- service URLs
- database connection settings
- worker/Redis settings
- environment mode selection

Rule: configuration must be centralized. Do not spread config lookups throughout random files.

### .env.example

This should provide a clean example of all expected environment variables for local and deployment setup.

It should:

- show required keys
- exclude real secrets
- be kept updated whenever configuration changes

### README.md

The backend should include a short README covering:

- what the service is
- how to run it
- how Docker is used
- how workers are started if used
- where migrations live
- where tests live

## 4. Routing and Service File Setup Standard

This project should follow a clear separation between routes and services.

### Route setup standard

- one route file per feature or endpoint group
- file names should be feature-based and easy to identify
- routes should remain thin and organized by API concern

Examples:

- routes/auth.py
- routes/users.py
- routes/orders.py
- routes/health.py

### Service setup standard

Services should be grouped by business domain.

```text
services/
├── users/
│   ├── service.py
│   ├── helpers.py
│   └── validators.py
├── auth/
│   ├── service.py
│   ├── helpers.py
│   └── exceptions.py
└── shared/
    ├── constants.py
    └── common.py
```

### Practical rule

- if a service domain has more than one or two files worth of logic, give it its own subfolder
- if the logic is still small, keep it as a single file
- avoid deeply nested service trees unless the project is genuinely large

The objective is compartmentalization without creating needless structure.

## 5. Logging, Environment, and Configuration Setup

### Logging setup

Logging should be explicitly configured and not improvised across the project.

Recommended approach:

- keep logging bootstrap/configuration in logging/config.py
- define one standard format for logs
- define the expected log levels by environment
- make sure all application parts use the same logging standard

The purpose is consistency and easier debugging.

### Environment setup

Environment variables should be represented through:

- .env.example for documentation
- actual environment files outside version control as needed
- centralized loading through config.py

### Configuration setup

config.py should be the single backend configuration entrypoint.
Use it to organize:

- app metadata and runtime settings
- database connection options
- Redis/worker settings
- third-party service settings
- feature toggles if any
- environment mode handling

Rule: do not hardcode operational values across routes, services, workers, or scripts.

## 6. Database Setup and Migration Options

The project may use one of the following database setup styles depending on project needs. The folder structure should support all three without confusion.

### Option A — Plain raw query setup using psycopg

Use this when: AI Executor asks you to.

Recommended structure impact:

- shared DB bootstrap remains in db.py
- raw SQL assets remain under sql/
- service files call into the database layer using the standard connection setup
- schema, migration, and seed files remain organized under sql/

### Option B — ORM-based setup

Use this when: AI Executor asks you to.

Recommended structure impact:

- ORM database setup still begins in db.py
- database-facing models remain in models/db/
- migration tooling output remains in sql/migrations/
- schema-related database assets still remain visible under sql/

### Option C — Supabase setup

Use this when: the project uses Supabase-managed database and platform services, or AI Executor asks you to.

Recommended structure impact:

- connection/config bootstrap remains centralized in db.py and config.py
- SQL assets that the project owns still remain under sql/
- any Supabase-related service wrappers should be kept under the relevant feature in services/

### Migration standard

Regardless of database option:

- migrations must have a dedicated home in sql/migrations/
- the migration approach must be documented in sql/README.md
- schema ownership should be clear
- migration history should not be scattered across multiple folders

## 7. Docker Setup Standard

The backend must be dockerized.

Required Docker-related files:

- Dockerfile
- docker-compose.yml
- .dockerignore

### Dockerfile

This should define the backend application container build.

### docker-compose.yml

This should define the local multi-service runtime setup where needed.

Typical services may include:

- backend API service
- database service
- Redis service
- worker service

### .dockerignore

This should exclude unnecessary files from the container build context, such as:

- virtual environments
- local caches
- local test artifacts
- git metadata where appropriate

### Docker standard rules

- Docker setup should be present from the start of the project, not added later as an afterthought.
- The compose setup should be readable and minimal.
- Local development services should be clearly named.
- Worker and Redis should be included when background processing is part of the design.

## 8. Worker Setup Standard

If the project needs background processing, use a dedicated worker setup with Redis/RQ.

### Worker folder placement

All worker-related files should live under workers/.

### Worker structure

Recommended:

```text
workers/
├── queue.py
├── jobs/
│   ├── notifications.py
│   ├── reports.py
│   └── cleanup.py
└── README.md
```

### Worker rules

- jobs should be grouped by domain or purpose
- worker setup should be separate from API route setup
- route files should not become worker setup files
- worker startup and queue details should be documented in workers/README.md

### When to add a worker

Add workers/ only when asynchronous or background tasks are actually required. Do not force a worker structure into a backend that does not need one.

## 9. Testing Setup Standard

Testing must be intentional, maintainable, and relevant. This is to ease the generation of QA Sheet which will be a non-negotiable deployment requirement going forward.

### Test structure

Recommended:

```text
tests/
├── conftest.py
├── fixtures/
├── routes/
├── services/
├── integration/
└── smoke/
```

### Test setup guidance

- routes/ — should contain endpoint-facing tests
- services/ — should contain business-logic-facing tests
- integration/ — should contain tests that validate interactions between important components
- smoke/ — should contain a very small set of high-value checks
- fixtures/ — should contain reusable setup only

### Important test policy

Only keep tests that are:

- relevant
- maintained
- useful for preventing regressions
- understandable by the team

Do not keep:

- placeholder tests
- duplicate tests
- obsolete tests for removed features
- tests nobody understands or maintains
- excessive low-value tests added only for coverage optics

Team rule: The repository should contain relevant tests only.
Test count is not the goal. Test usefulness is the goal.

## 10. Simplicity Rules

To keep the SOP practical, the team should follow these simplicity rules:

- Start flat, then add subfolders only when justified.
- Do not create layers that the project size does not need.
- Keep file naming obvious and feature-based.
- Keep all operational setup in known standard locations.
- Prefer consistency over cleverness.
- Every new folder should have a clear purpose.
- If a folder becomes a dumping ground, reorganize it.

This structure is meant to improve SDLC, not create ceremony.

## 11. Example Structures

### Example A — Small backend

Use a simpler version for a small service.

```text
backend/
├── routes/
│   ├── health.py
│   └── users.py
├── services/
│   ├── users.py
│   └── auth.py
├── models/
│   ├── user.py
│   └── auth.py
├── utils/
├── sql/
│   ├── schema/
│   └── migrations/
├── tests/
│   ├── routes/
│   └── services/
├── scripts/
├── app.py
├── db.py
├── config.py
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

This is appropriate when the backend is small and feature count is limited.

### Example B — Medium backend with service subfolders

Use this when logic begins to grow by domain.

```text
backend/
├── routes/
│   ├── auth.py
│   ├── users.py
│   ├── orders.py
│   └── health.py
├── services/
│   ├── auth/
│   │   ├── service.py
│   │   ├── helpers.py
│   │   └── exceptions.py
│   ├── users/
│   │   ├── service.py
│   │   ├── validators.py
│   │   └── helpers.py
│   └── orders/
│       ├── service.py
│       └── helpers.py
├── models/
│   ├── db/
│   ├── domain/
│   └── schemas/
├── utils/
├── sql/
│   ├── schema/
│   ├── migrations/
│   └── seeds/
├── tests/
│   ├── fixtures/
│   ├── routes/
│   ├── services/
│   └── integration/
├── scripts/
├── app.py
├── db.py
├── config.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

This is the recommended default shape for most team projects.

### Example C — Backend with worker support

Use this when background jobs are required.

```text
backend/
├── routes/
├── services/
├── models/
├── utils/
├── sql/
├── tests/
├── scripts/
├── workers/
│   ├── queue.py
│   └── jobs/
│       ├── notifications.py
│       └── reports.py
├── app.py
├── db.py
├── config.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

This should be used only when the worker is actually needed.

## 12. Final Team Standard

Every FastAPI backend in this team should:

- live under backend/
- separate routes, services, models, utils, SQL assets, scripts, tests, and workers clearly
- centralize app startup in app.py
- centralize DB setup in db.py
- centralize config in config.py
- provide Docker setup from the beginning
- include worker structure only when needed
- keep tests relevant and maintainable
- avoid unnecessary complexity

This SOP is the default standard unless a project has a strong
and documented reason to differ.
